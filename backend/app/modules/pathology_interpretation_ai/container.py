"""Module composition root for the AI Pathology Interpretation module.

Scope note — this task builds a **generation-only, interpretation-only**
module: it interprets a *textual* pathology report and produces a
structured `PathologyInterpretationResult`, and never interprets
microscope images or whole-slide images, persists results, or replaces
pathologist review. Owns no database session or per-request state, so
every component here is process-lifetime and exposed as an `lru_cache`d
singleton, the same shape every prior AI module's own `container.py`
uses for itself.

**Genuine reuse of `app.modules.medical_reasoning_ai`** — this task's
own REUSE section names "AI Medical Reasoning Engine" explicitly.
`application/use_cases/interpret_pathology_report.py
::InterpretPathologyReportUseCase` depends directly on that peer
module's own public port,
`app.modules.medical_reasoning_ai.public.interfaces.MedicalReasoningAIPort`,
constructed here via that peer module's own `container.py
.get_medical_reasoning_ai_facade` — the exact same "import a peer
module's `public/` package, plus its `container.py` factory function to
construct one" precedent `app.modules.lab_interpretation_ai.container`/
`app.modules.radiology_interpretation_ai.container` already establish
for themselves: `score_confidence` backs this module's own confidence-
scoring enrichment step, using `len(reconciled_findings)` as the
`supporting_count` — the closest analog this module's own findings-based
OUTPUT has to that port's generic "supporting evidence" concept.

**Why `app.modules.lab_interpretation_ai`/
`app.modules.radiology_interpretation_ai` are not called into directly**
— this task's own SUPPORTED INPUT section lists "Laboratory
Interpretation" and "Radiology Interpretation" as accepted inputs, but as
plain, caller-supplied `str | None` fields on
`PathologyInterpretationInput` (`laboratory_interpretation`,
`radiology_interpretation`), not a live call into either module's own
generation pipeline — the same "explicit input, not a live cross-module
lookup" design this module's own `domain/value_objects.py` module
docstring documents in full. Neither peer module's public port exposes a
standalone, primitive-typed capability that this module could reuse
without triggering a second, unrequested AI generation (unlike
`MedicalReasoningAIPort.score_confidence`) — `app.modules
.radiology_interpretation_ai.public.interfaces
.RadiologyInterpretationAIPort.extract_candidate_findings` returns its
own module's `RadiologyFinding` type, not this module's own
`PathologyFinding`, so calling it would require conversion for no real
benefit over this module's own `ClinicalCorrelationPort` — so there is
no genuine reuse opportunity there beyond the architectural pattern, the
same "reuse the pattern, not the code" conclusion reached for the AI
Clinical Copilot/Clinical Note AI/SOAP Note AI/ICD-10 AI/Prescription
AI/Differential Diagnosis AI modules throughout every prior phase.

REUSE, for everything else, is satisfied exactly as it was for
`app.modules.radiology_interpretation_ai` (see that module's own
`container.py` scope note for the identical reasoning): (1) AI
Foundation directly (`AIGatewayPort`, `PromptRegistry`), and (2) the
genuinely module-agnostic mechanics in `app.shared.infrastructure
.text_processing` (JSON extraction, placeholder detection, word-chunked
streaming). "Shared renderer" is satisfied by `application/services
/pathology_summary_service.PathologySummaryService` following the
identical JSON/Markdown/text rendering shape every prior AI module's own
renderer already established. "Shared audit infrastructure" is likewise
the `structlog`-via-`app.core.logging.get_logger` pattern every prior AI
module's own audit logger already uses. Provider selection, cost
estimation, and template registration remain this module's own small,
locally-owned copies for the same reason
`app.shared.infrastructure.text_processing`'s own module docstrings
give: they need AI Foundation's own types, and `app/shared/` may never
import from `app/modules/`.
"""

from functools import lru_cache

from app.core.config import get_settings
from app.modules.ai.container import get_ai_gateway_facade, get_prompt_registry
from app.modules.medical_reasoning_ai.container import get_medical_reasoning_ai_facade
from app.modules.pathology_interpretation_ai.application.ports import (
    ClinicalCorrelationPort,
    CostEstimatorPort,
    PathologyInterpretationAuditLoggerPort,
    PathologyInterpretationParserPort,
    PathologyInterpretationTemplateSelectorPort,
    PathologyInterpretationValidatorPort,
    PathologyInterpreterPort,
    PathologyPromptBuilderPort,
)
from app.modules.pathology_interpretation_ai.application.services.clinical_correlation_service import (  # noqa: E501
    ClinicalCorrelationService,
)
from app.modules.pathology_interpretation_ai.application.services.finding_extraction_service import (  # noqa: E501
    FindingExtractionService,
)
from app.modules.pathology_interpretation_ai.application.services.malignancy_assessment_service import (  # noqa: E501
    MalignancyAssessmentService,
)
from app.modules.pathology_interpretation_ai.application.services.pathology_summary_service import (  # noqa: E501
    PathologySummaryService,
)
from app.modules.pathology_interpretation_ai.application.use_cases.interpret_pathology_report import (  # noqa: E501
    InterpretPathologyReportUseCase,
)
from app.modules.pathology_interpretation_ai.infrastructure.audit.audit_logger import (
    StructlogPathologyInterpretationAuditLogger,
)
from app.modules.pathology_interpretation_ai.infrastructure.clinical_correlation.keyword_clinical_correlator import (  # noqa: E501
    KeywordClinicalCorrelator,
)
from app.modules.pathology_interpretation_ai.infrastructure.cost.cost_estimator import (
    CostEstimator,
)
from app.modules.pathology_interpretation_ai.infrastructure.generation.pathology_interpretation_generator import (  # noqa: E501
    DefaultPathologyInterpretationGenerator,
)
from app.modules.pathology_interpretation_ai.infrastructure.parsing.pathology_interpretation_parser import (  # noqa: E501
    DefaultPathologyInterpretationParser,
)
from app.modules.pathology_interpretation_ai.infrastructure.prompts.prompt_builder import (
    DefaultPathologyPromptBuilder,
)
from app.modules.pathology_interpretation_ai.infrastructure.prompts.template_selector import (
    DefaultPathologyInterpretationTemplateSelector,
)
from app.modules.pathology_interpretation_ai.infrastructure.provider_selection import (
    resolve_default_ai_model,
)
from app.modules.pathology_interpretation_ai.infrastructure.validation.pathology_interpretation_validator import (  # noqa: E501
    DefaultPathologyInterpretationValidator,
)
from app.modules.pathology_interpretation_ai.public.facade import PathologyInterpretationAIFacade


@lru_cache
def get_output_parser() -> PathologyInterpretationParserPort:
    return DefaultPathologyInterpretationParser()


@lru_cache
def get_clinical_correlator() -> ClinicalCorrelationPort:
    return KeywordClinicalCorrelator()


@lru_cache
def get_finding_extraction_service() -> FindingExtractionService:
    return FindingExtractionService(correlator=get_clinical_correlator())


@lru_cache
def get_malignancy_assessment_service() -> MalignancyAssessmentService:
    return MalignancyAssessmentService(correlator=get_clinical_correlator())


@lru_cache
def get_correlation_service() -> ClinicalCorrelationService:
    return ClinicalCorrelationService()


@lru_cache
def get_summary_service() -> PathologySummaryService:
    return PathologySummaryService()


@lru_cache
def get_result_validator() -> PathologyInterpretationValidatorPort:
    return DefaultPathologyInterpretationValidator(correlation_service=get_correlation_service())


@lru_cache
def get_pathology_interpretation_audit_logger() -> PathologyInterpretationAuditLoggerPort:
    return StructlogPathologyInterpretationAuditLogger()


@lru_cache
def get_cost_estimator() -> CostEstimatorPort:
    return CostEstimator()


@lru_cache
def get_template_selector() -> PathologyInterpretationTemplateSelectorPort:
    return DefaultPathologyInterpretationTemplateSelector()


@lru_cache
def get_prompt_builder() -> PathologyPromptBuilderPort:
    return DefaultPathologyPromptBuilder(ai_gateway=get_ai_gateway_facade())


@lru_cache
def get_pathology_interpretation_generator() -> PathologyInterpreterPort:
    settings = get_settings()
    return DefaultPathologyInterpretationGenerator(
        ai_gateway=get_ai_gateway_facade(),
        prompt_registry=get_prompt_registry(),
        template_selector=get_template_selector(),
        prompt_builder=get_prompt_builder(),
        cost_estimator=get_cost_estimator(),
        default_model=resolve_default_ai_model(settings),
    )


@lru_cache
def get_pathology_interpretation_ai_facade() -> PathologyInterpretationAIFacade:
    generator = get_pathology_interpretation_generator()
    generate_use_case = InterpretPathologyReportUseCase(
        generator=generator,
        parser=get_output_parser(),
        validator=get_result_validator(),
        finding_extraction_service=get_finding_extraction_service(),
        malignancy_assessment_service=get_malignancy_assessment_service(),
        correlation_service=get_correlation_service(),
        medical_reasoning=get_medical_reasoning_ai_facade(),
        audit_logger=get_pathology_interpretation_audit_logger(),
    )
    return PathologyInterpretationAIFacade(
        generate_use_case=generate_use_case,
        finding_extraction_service=get_finding_extraction_service(),
        summary_service=get_summary_service(),
        generator=generator,
    )
