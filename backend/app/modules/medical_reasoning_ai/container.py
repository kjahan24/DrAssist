"""Module composition root for the AI Medical Reasoning Engine.

Scope note — this task builds a **generation-only, reasoning-only**
module: it produces a structured `MedicalReasoningResult` from explicit
clinical evidence and never persists, diagnoses, prescribes, or replaces
physician judgment on anything. This task's own GOAL section is explicit
that this module "is NOT an endpoint that clinicians use directly" — it
exists to be called *by other backend modules* through `public
/interfaces.py::MedicalReasoningAIPort`, not by a clinician-facing HTTP
client (see `presentation/router.py`'s own docstring for how that shapes
its placeholder-only HTTP surface).

**Why the six existing AI modules are not wired to call through this one
in this task** — this task's own IMPORTANT RULES are unambiguous: "Never
redesign completed modules. Never modify completed backend modules
unless strictly required for dependency injection." `app.modules
.ai_copilot`, `app.modules.clinical_note_ai`, `app.modules.soap_note_ai`,
`app.modules.icd10_ai`, `app.modules.prescription_ai`, and
`app.modules.differential_diagnosis_ai` are all completed, already-
verified, SAFE-TO-COMMIT modules from prior phases — each already
performs its own reasoning (parsing, validation, confidence handling)
end to end and functions correctly without this module. Retrofitting any
of them to route through `MedicalReasoningAIPort` would be exactly the
kind of modification this task forbids: not "strictly required for
dependency injection" (none of them are broken or incomplete without
it), but a redesign of their internal pipelines. This task is therefore
scoped to building the reasoning engine itself, fully production-ready
and independently usable, so that it is *available* as the shared layer
future modules are expected to depend on ("Future AI modules" — this
task's own words) — the module fulfills its GOAL by existing and being
SAFE TO COMMIT, not by being force-wired into modules that were
explicitly placed off-limits to modification.

REUSE, per this task's own section — "AI Foundation, Shared parser,
Shared prompt framework, Shared validator, Shared renderer, Shared
streaming, Shared audit infrastructure": satisfied exactly as it was for
`app.modules.differential_diagnosis_ai` (see that module's own
`container.py` scope note for the identical reasoning): (1) AI
Foundation directly (`AIGatewayPort`, `PromptRegistry`), and (2) the
genuinely module-agnostic mechanics in `app.shared.infrastructure
.text_processing` (JSON extraction, placeholder detection, word-chunked
streaming) — these *are* this codebase's "shared parser"/"shared
validator"/"shared streaming" framework, used directly rather than
reimplemented. "Shared renderer" is satisfied by
`application/services/clinical_summary_service.ClinicalSummaryService`
following the identical JSON/Markdown/text rendering shape every prior
AI module's own renderer already established (there is no separate
shared renderer *class* in this codebase to import — each module's
renderer is a small, independently-owned implementation of the same
pattern, the same "architectural pattern reuse, not internals reuse"
conclusion `app.modules.differential_diagnosis_ai.container`'s own
REUSE discussion reaches). "Shared audit infrastructure" is likewise the
`structlog`-via-`app.core.logging.get_logger` pattern every prior AI
module's own audit logger already uses, applied here identically.
Provider selection, cost estimation, and template registration remain
this module's own small, locally-owned copies for the same reason
`app.shared.infrastructure.text_processing`'s own module docstrings
give: they need AI Foundation's own types, and `app/shared/` may never
import from `app/modules/`.

This module's input is fully self-contained clinical evidence, not an
`app.modules.ai_copilot`-style patient-history lookup — the same
"explicit encounter input only" design `app.modules.clinical_note_ai`/
`app.modules.soap_note_ai`/`app.modules.icd10_ai`/
`app.modules.prescription_ai`/`app.modules.differential_diagnosis_ai`
all use for themselves.

Owns no database session or per-request state (no persistence at all),
so every component here is process-lifetime and exposed as an
`lru_cache`d singleton, the same shape
`app.modules.differential_diagnosis_ai.container` uses for itself.
"""

from functools import lru_cache

from app.core.config import get_settings
from app.modules.ai.container import get_ai_gateway_facade, get_prompt_registry
from app.modules.medical_reasoning_ai.application.ports import (
    ConfidenceCalculatorPort,
    CostEstimatorPort,
    EvidenceAnalyzerPort,
    MedicalReasoningAuditLoggerPort,
    MedicalReasoningParserPort,
    MedicalReasoningPort,
    MedicalReasoningTemplateSelectorPort,
    MedicalReasoningValidatorPort,
    ReasoningPromptBuilderPort,
)
from app.modules.medical_reasoning_ai.application.services.clinical_summary_service import (
    ClinicalSummaryService,
)
from app.modules.medical_reasoning_ai.application.services.confidence_scoring_service import (
    ConfidenceScoringService,
)
from app.modules.medical_reasoning_ai.application.services.evidence_analysis_service import (
    EvidenceAnalysisService,
)
from app.modules.medical_reasoning_ai.application.services.recommendation_reasoning_service import (
    RecommendationReasoningService,
)
from app.modules.medical_reasoning_ai.application.use_cases.generate_clinical_reasoning import (
    GenerateClinicalReasoningUseCase,
)
from app.modules.medical_reasoning_ai.infrastructure.audit.audit_logger import (
    StructlogMedicalReasoningAuditLogger,
)
from app.modules.medical_reasoning_ai.infrastructure.confidence.default_confidence_calculator import (  # noqa: E501
    DefaultConfidenceCalculator,
)
from app.modules.medical_reasoning_ai.infrastructure.cost.cost_estimator import CostEstimator
from app.modules.medical_reasoning_ai.infrastructure.generation.medical_reasoning_generator import (
    DefaultMedicalReasoningGenerator,
)
from app.modules.medical_reasoning_ai.infrastructure.parsing.medical_reasoning_parser import (
    DefaultMedicalReasoningParser,
)
from app.modules.medical_reasoning_ai.infrastructure.prompts.prompt_builder import (
    DefaultReasoningPromptBuilder,
)
from app.modules.medical_reasoning_ai.infrastructure.prompts.template_selector import (
    DefaultMedicalReasoningTemplateSelector,
)
from app.modules.medical_reasoning_ai.infrastructure.provider_selection import (
    resolve_default_ai_model,
)
from app.modules.medical_reasoning_ai.infrastructure.reasoning.default_evidence_analyzer import (
    DefaultEvidenceAnalyzer,
)
from app.modules.medical_reasoning_ai.infrastructure.validation.medical_reasoning_validator import (
    DefaultMedicalReasoningValidator,
)
from app.modules.medical_reasoning_ai.public.facade import MedicalReasoningAIFacade


@lru_cache
def get_output_parser() -> MedicalReasoningParserPort:
    return DefaultMedicalReasoningParser()


@lru_cache
def get_evidence_analyzer() -> EvidenceAnalyzerPort:
    return DefaultEvidenceAnalyzer()


@lru_cache
def get_confidence_calculator() -> ConfidenceCalculatorPort:
    return DefaultConfidenceCalculator()


@lru_cache
def get_evidence_service() -> EvidenceAnalysisService:
    return EvidenceAnalysisService(analyzer=get_evidence_analyzer())


@lru_cache
def get_confidence_service() -> ConfidenceScoringService:
    return ConfidenceScoringService(calculator=get_confidence_calculator())


@lru_cache
def get_recommendation_service() -> RecommendationReasoningService:
    return RecommendationReasoningService()


@lru_cache
def get_summary_service() -> ClinicalSummaryService:
    return ClinicalSummaryService()


@lru_cache
def get_result_validator() -> MedicalReasoningValidatorPort:
    return DefaultMedicalReasoningValidator(
        evidence_service=get_evidence_service(),
        recommendation_service=get_recommendation_service(),
    )


@lru_cache
def get_medical_reasoning_audit_logger() -> MedicalReasoningAuditLoggerPort:
    return StructlogMedicalReasoningAuditLogger()


@lru_cache
def get_cost_estimator() -> CostEstimatorPort:
    return CostEstimator()


@lru_cache
def get_template_selector() -> MedicalReasoningTemplateSelectorPort:
    return DefaultMedicalReasoningTemplateSelector()


@lru_cache
def get_prompt_builder() -> ReasoningPromptBuilderPort:
    return DefaultReasoningPromptBuilder(ai_gateway=get_ai_gateway_facade())


@lru_cache
def get_medical_reasoning_generator() -> MedicalReasoningPort:
    settings = get_settings()
    return DefaultMedicalReasoningGenerator(
        ai_gateway=get_ai_gateway_facade(),
        prompt_registry=get_prompt_registry(),
        template_selector=get_template_selector(),
        prompt_builder=get_prompt_builder(),
        cost_estimator=get_cost_estimator(),
        default_model=resolve_default_ai_model(settings),
    )


@lru_cache
def get_medical_reasoning_ai_facade() -> MedicalReasoningAIFacade:
    generator = get_medical_reasoning_generator()
    generate_use_case = GenerateClinicalReasoningUseCase(
        generator=generator,
        parser=get_output_parser(),
        validator=get_result_validator(),
        evidence_service=get_evidence_service(),
        confidence_service=get_confidence_service(),
        recommendation_service=get_recommendation_service(),
        audit_logger=get_medical_reasoning_audit_logger(),
    )
    return MedicalReasoningAIFacade(
        generate_use_case=generate_use_case,
        evidence_service=get_evidence_service(),
        confidence_service=get_confidence_service(),
        summary_service=get_summary_service(),
        generator=generator,
    )
