"""Module composition root for the AI Patient Education & Discharge
Instructions module.

Scope note — this task builds a **generation-only, educational-support-
only** module: it turns caller-supplied diagnoses/medications/clinical
context into a structured `PatientEducationResult`, and never replaces
physician counselling, persists anything, or issues a directive medical
order. Owns no database session or per-request state, so every
component here is process-lifetime and exposed as an `lru_cache`d
singleton, the same shape every prior AI module's own `container.py`
uses for itself.

**Genuine reuse of `app.modules.medical_reasoning_ai`** — this task's
own SUPPORTED INPUT section names "Medical Reasoning" among its own
peer-module inputs, and this module reuses `app.modules
.medical_reasoning_ai` the same genuine way every interpretation-AI
module since Phase 4.9 has: `application/use_cases
/generate_patient_education.py::GeneratePatientEducationUseCase`
depends directly on that peer module's own public port,
`app.modules.medical_reasoning_ai.public.interfaces.MedicalReasoningAIPort`,
constructed here via that peer module's own `container.py
.get_medical_reasoning_ai_facade` — the exact same "import a peer
module's `public/` package, plus its `container.py` factory function to
construct one" precedent every prior interpretation-AI module's own
`container.py` already establishes for itself: `score_confidence` backs
this module's own confidence-scoring enrichment step, using
`len(medication_instructions) + len(warning_signs)` as the
`supporting_count` — the closest analog this module's own
recommendation-based OUTPUT has to that port's generic "supporting
evidence" concept.

**Why `app.modules.prescription_ai`/`drug_interaction_ai`/
`risk_stratification_ai`/`lab_interpretation_ai`/
`radiology_interpretation_ai`/`pathology_interpretation_ai`/
`differential_diagnosis_ai` are not called into directly** — this
task's own SUPPORTED INPUT section names all seven of these peer
modules' own outputs explicitly, alongside "Clinical Notes"/"SOAP
Notes". Each of those seven peer modules' own public port exposes only
a full `generate_*`/`analyze_*`/`interpret_*` **generation pipeline** of
its own — accepting *its own* structured input value object and
producing *its own* `Generated*` result, not a lookup this module could
call mid-pipeline. Calling into any of them here would mean this module
either re-running an entire sibling generation pipeline itself (a
second, redundant AI call and a second audit trail this task's own
SUPPORTED INPUT list does not ask for) or fabricating that sibling
module's own structured input from data this module was never given.
This task's own wording reads as "accept an already-generated summary
as context", not "generate one yourself" — the same conclusion
`app.modules.risk_stratification_ai.container`'s own scope note reaches
for its own, structurally identical, seven-peer-module SUPPORTED INPUT
list. `domain/value_objects.py::PatientEducationInput` therefore models
all seven as plain `str | None` fields the caller populates with
whatever summary text it already has, the same "explicit input, not a
live cross-module lookup" design every prior AI module's own
peer-module context fields establish for themselves.

REUSE, for everything else, is satisfied exactly as it was for
`app.modules.risk_stratification_ai` (see that module's own
`container.py` scope note for the identical reasoning): (1) AI
Foundation directly (`AIGatewayPort`, `PromptRegistry`), and (2) the
genuinely module-agnostic mechanics in `app.shared.infrastructure
.text_processing` (JSON extraction, placeholder detection, word-chunked
streaming). "Shared renderer" is satisfied by `application/services
/patient_education_report_renderer.PatientEducationReportRenderer`
following the identical JSON/Markdown/text rendering shape every prior
AI module's own renderer already established. "Shared audit
infrastructure" is likewise the `structlog`-via-`app.core.logging
.get_logger` pattern every prior AI module's own audit logger already
uses. Provider selection, cost estimation, and template registration
remain this module's own small, locally-owned copies for the same
reason `app.shared.infrastructure.text_processing`'s own module
docstrings give: they need AI Foundation's own types, and `app/shared/`
may never import from `app/modules/`.
"""

from functools import lru_cache

from app.core.config import get_settings
from app.modules.ai.container import get_ai_gateway_facade, get_prompt_registry
from app.modules.medical_reasoning_ai.container import get_medical_reasoning_ai_facade
from app.modules.patient_education_ai.application.ports import (
    CostEstimatorPort,
    DischargeInstructionPort,
    LifestyleRecommendationPort,
    PatientEducationAnalysisAuditLoggerPort,
    PatientEducationAnalysisGeneratorPort,
    PatientEducationAnalysisParserPort,
    PatientEducationAnalysisPromptBuilderPort,
    PatientEducationAnalysisTemplateSelectorPort,
    PatientEducationAnalysisValidatorPort,
    PatientEducationPort,
)
from app.modules.patient_education_ai.application.services.discharge_instruction_service import (
    DischargeInstructionService,
)
from app.modules.patient_education_ai.application.services.lifestyle_recommendation_service import (  # noqa: E501
    LifestyleRecommendationService,
)
from app.modules.patient_education_ai.application.services.patient_education_report_renderer import (  # noqa: E501
    PatientEducationReportRenderer,
)
from app.modules.patient_education_ai.application.services.patient_education_service import (
    PatientEducationService,
)
from app.modules.patient_education_ai.application.use_cases.generate_patient_education import (
    GeneratePatientEducationUseCase,
)
from app.modules.patient_education_ai.infrastructure.audit.audit_logger import (
    StructlogPatientEducationAuditLogger,
)
from app.modules.patient_education_ai.infrastructure.cost.cost_estimator import CostEstimator
from app.modules.patient_education_ai.infrastructure.discharge_instruction.static_discharge_instruction_knowledge_base import (  # noqa: E501
    StaticDischargeInstructionKnowledgeBase,
)
from app.modules.patient_education_ai.infrastructure.generation.patient_education_generator import (  # noqa: E501
    DefaultPatientEducationAnalysisGenerator,
)
from app.modules.patient_education_ai.infrastructure.lifestyle_recommendation.static_lifestyle_recommendation_knowledge_base import (  # noqa: E501
    StaticLifestyleRecommendationKnowledgeBase,
)
from app.modules.patient_education_ai.infrastructure.parsing.patient_education_parser import (
    DefaultPatientEducationAnalysisParser,
)
from app.modules.patient_education_ai.infrastructure.patient_education.static_patient_education_knowledge_base import (  # noqa: E501
    StaticPatientEducationKnowledgeBase,
)
from app.modules.patient_education_ai.infrastructure.prompts.prompt_builder import (
    DefaultPatientEducationAnalysisPromptBuilder,
)
from app.modules.patient_education_ai.infrastructure.prompts.template_selector import (
    DefaultPatientEducationAnalysisTemplateSelector,
)
from app.modules.patient_education_ai.infrastructure.provider_selection import (
    resolve_default_ai_model,
)
from app.modules.patient_education_ai.infrastructure.validation.patient_education_validator import (  # noqa: E501
    DefaultPatientEducationAnalysisValidator,
)
from app.modules.patient_education_ai.public.facade import PatientEducationAIFacade


@lru_cache
def get_output_parser() -> PatientEducationAnalysisParserPort:
    return DefaultPatientEducationAnalysisParser()


@lru_cache
def get_patient_education_port() -> PatientEducationPort:
    return StaticPatientEducationKnowledgeBase()


@lru_cache
def get_discharge_instruction_port() -> DischargeInstructionPort:
    return StaticDischargeInstructionKnowledgeBase()


@lru_cache
def get_lifestyle_recommendation_port() -> LifestyleRecommendationPort:
    return StaticLifestyleRecommendationKnowledgeBase()


@lru_cache
def get_patient_education_service() -> PatientEducationService:
    return PatientEducationService(education_port=get_patient_education_port())


@lru_cache
def get_discharge_instruction_service() -> DischargeInstructionService:
    return DischargeInstructionService(discharge_instruction_port=get_discharge_instruction_port())


@lru_cache
def get_lifestyle_recommendation_service() -> LifestyleRecommendationService:
    return LifestyleRecommendationService(
        lifestyle_recommendation_port=get_lifestyle_recommendation_port()
    )


@lru_cache
def get_renderer() -> PatientEducationReportRenderer:
    return PatientEducationReportRenderer()


@lru_cache
def get_result_validator() -> PatientEducationAnalysisValidatorPort:
    return DefaultPatientEducationAnalysisValidator()


@lru_cache
def get_patient_education_audit_logger() -> PatientEducationAnalysisAuditLoggerPort:
    return StructlogPatientEducationAuditLogger()


@lru_cache
def get_cost_estimator() -> CostEstimatorPort:
    return CostEstimator()


@lru_cache
def get_template_selector() -> PatientEducationAnalysisTemplateSelectorPort:
    return DefaultPatientEducationAnalysisTemplateSelector()


@lru_cache
def get_prompt_builder() -> PatientEducationAnalysisPromptBuilderPort:
    return DefaultPatientEducationAnalysisPromptBuilder(ai_gateway=get_ai_gateway_facade())


@lru_cache
def get_patient_education_generator() -> PatientEducationAnalysisGeneratorPort:
    settings = get_settings()
    return DefaultPatientEducationAnalysisGenerator(
        ai_gateway=get_ai_gateway_facade(),
        prompt_registry=get_prompt_registry(),
        template_selector=get_template_selector(),
        prompt_builder=get_prompt_builder(),
        cost_estimator=get_cost_estimator(),
        default_model=resolve_default_ai_model(settings),
    )


@lru_cache
def get_patient_education_ai_facade() -> PatientEducationAIFacade:
    generator = get_patient_education_generator()
    generate_use_case = GeneratePatientEducationUseCase(
        generator=generator,
        parser=get_output_parser(),
        validator=get_result_validator(),
        patient_education_service=get_patient_education_service(),
        discharge_instruction_service=get_discharge_instruction_service(),
        lifestyle_recommendation_service=get_lifestyle_recommendation_service(),
        medical_reasoning=get_medical_reasoning_ai_facade(),
        audit_logger=get_patient_education_audit_logger(),
    )
    return PatientEducationAIFacade(
        generate_use_case=generate_use_case,
        renderer=get_renderer(),
        generator=generator,
    )
