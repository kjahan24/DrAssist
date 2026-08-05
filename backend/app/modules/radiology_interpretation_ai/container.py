"""Module composition root for the AI Radiology Interpretation module.

Scope note — this task builds a **generation-only, interpretation-only**
module: it interprets a *textual* radiology report and produces a
structured `RadiologyInterpretationResult`, and never interprets raw
DICOM images, persists results, or replaces radiologist review. Owns no
database session or per-request state, so every component here is
process-lifetime and exposed as an `lru_cache`d singleton, the same
shape every prior AI module's own `container.py` uses for itself.

**Genuine reuse of `app.modules.medical_reasoning_ai`** — this task's
own REUSE section names "AI Medical Reasoning Engine" explicitly.
`application/use_cases/interpret_radiology_report.py
::InterpretRadiologyReportUseCase` depends directly on that peer
module's own public port,
`app.modules.medical_reasoning_ai.public.interfaces.MedicalReasoningAIPort`,
constructed here via that peer module's own `container.py
.get_medical_reasoning_ai_facade` — the exact same "import a peer
module's `public/` package, plus its `container.py` factory function to
construct one" precedent
`app.modules.lab_interpretation_ai.container` already establishes for
itself (see that module's own `container.py` module docstring for the
full reasoning, which applies identically here): `score_confidence`
backs this module's own confidence-scoring enrichment step, using
`len(reconciled_findings)` as the `supporting_count` — the closest
analog this module's own findings-based OUTPUT has to that port's
generic "supporting evidence" concept.

**Why `app.modules.lab_interpretation_ai` is not called into directly**
— this task's own SUPPORTED INPUT section lists "Laboratory
Interpretation" as an accepted input, but as a plain, caller-supplied
`str | None` field on `RadiologyInterpretationInput`
(`laboratory_interpretation`), not a live call into that module's own
generation pipeline — the same "explicit input, not a live cross-module
lookup" design this module's own `domain/value_objects.py` module
docstring documents in full. Unlike `MedicalReasoningAIPort`,
`app.modules.lab_interpretation_ai.public.interfaces
.LabInterpretationAIPort` exposes no standalone, primitive-typed
capability (only a full `generate_interpretation` pipeline call) that
this module could reuse without triggering a second, unrequested AI
generation — so there is no genuine reuse opportunity there beyond the
architectural pattern, the same "reuse the pattern, not the code"
conclusion reached for the AI Clinical Copilot/Clinical Note AI/SOAP
Note AI/ICD-10 AI/Prescription AI/Differential Diagnosis AI modules
throughout every prior phase.

REUSE, for everything else, is satisfied exactly as it was for
`app.modules.lab_interpretation_ai` (see that module's own `container.py`
scope note for the identical reasoning): (1) AI Foundation directly
(`AIGatewayPort`, `PromptRegistry`), and (2) the genuinely module-
agnostic mechanics in `app.shared.infrastructure.text_processing` (JSON
extraction, placeholder detection, word-chunked streaming). "Shared
renderer" is satisfied by `application/services
/radiology_summary_service.RadiologySummaryService` following the
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
from app.modules.radiology_interpretation_ai.application.ports import (
    CostEstimatorPort,
    FindingExtractionPort,
    RadiologyInterpretationAuditLoggerPort,
    RadiologyInterpretationParserPort,
    RadiologyInterpretationTemplateSelectorPort,
    RadiologyInterpretationValidatorPort,
    RadiologyInterpreterPort,
    RadiologyPromptBuilderPort,
)
from app.modules.radiology_interpretation_ai.application.services.critical_finding_detection_service import (  # noqa: E501
    CriticalFindingDetectionService,
)
from app.modules.radiology_interpretation_ai.application.services.finding_extraction_service import (  # noqa: E501
    FindingExtractionService,
)
from app.modules.radiology_interpretation_ai.application.services.follow_up_recommendation_service import (  # noqa: E501
    FollowUpRecommendationService,
)
from app.modules.radiology_interpretation_ai.application.services.radiology_summary_service import (  # noqa: E501
    RadiologySummaryService,
)
from app.modules.radiology_interpretation_ai.application.use_cases.interpret_radiology_report import (  # noqa: E501
    InterpretRadiologyReportUseCase,
)
from app.modules.radiology_interpretation_ai.infrastructure.audit.audit_logger import (
    StructlogRadiologyInterpretationAuditLogger,
)
from app.modules.radiology_interpretation_ai.infrastructure.cost.cost_estimator import (
    CostEstimator,
)
from app.modules.radiology_interpretation_ai.infrastructure.finding_extraction.keyword_radiology_finding_extractor import (  # noqa: E501
    KeywordRadiologyFindingExtractor,
)
from app.modules.radiology_interpretation_ai.infrastructure.generation.radiology_interpretation_generator import (  # noqa: E501
    DefaultRadiologyInterpretationGenerator,
)
from app.modules.radiology_interpretation_ai.infrastructure.parsing.radiology_interpretation_parser import (  # noqa: E501
    DefaultRadiologyInterpretationParser,
)
from app.modules.radiology_interpretation_ai.infrastructure.prompts.prompt_builder import (
    DefaultRadiologyPromptBuilder,
)
from app.modules.radiology_interpretation_ai.infrastructure.prompts.template_selector import (
    DefaultRadiologyInterpretationTemplateSelector,
)
from app.modules.radiology_interpretation_ai.infrastructure.provider_selection import (
    resolve_default_ai_model,
)
from app.modules.radiology_interpretation_ai.infrastructure.validation.radiology_interpretation_validator import (  # noqa: E501
    DefaultRadiologyInterpretationValidator,
)
from app.modules.radiology_interpretation_ai.public.facade import RadiologyInterpretationAIFacade


@lru_cache
def get_output_parser() -> RadiologyInterpretationParserPort:
    return DefaultRadiologyInterpretationParser()


@lru_cache
def get_finding_extractor() -> FindingExtractionPort:
    return KeywordRadiologyFindingExtractor()


@lru_cache
def get_finding_extraction_service() -> FindingExtractionService:
    return FindingExtractionService(extractor=get_finding_extractor())


@lru_cache
def get_critical_finding_service() -> CriticalFindingDetectionService:
    return CriticalFindingDetectionService(extractor=get_finding_extractor())


@lru_cache
def get_recommendation_service() -> FollowUpRecommendationService:
    return FollowUpRecommendationService()


@lru_cache
def get_summary_service() -> RadiologySummaryService:
    return RadiologySummaryService()


@lru_cache
def get_result_validator() -> RadiologyInterpretationValidatorPort:
    return DefaultRadiologyInterpretationValidator(
        recommendation_service=get_recommendation_service()
    )


@lru_cache
def get_radiology_interpretation_audit_logger() -> RadiologyInterpretationAuditLoggerPort:
    return StructlogRadiologyInterpretationAuditLogger()


@lru_cache
def get_cost_estimator() -> CostEstimatorPort:
    return CostEstimator()


@lru_cache
def get_template_selector() -> RadiologyInterpretationTemplateSelectorPort:
    return DefaultRadiologyInterpretationTemplateSelector()


@lru_cache
def get_prompt_builder() -> RadiologyPromptBuilderPort:
    return DefaultRadiologyPromptBuilder(ai_gateway=get_ai_gateway_facade())


@lru_cache
def get_radiology_interpretation_generator() -> RadiologyInterpreterPort:
    settings = get_settings()
    return DefaultRadiologyInterpretationGenerator(
        ai_gateway=get_ai_gateway_facade(),
        prompt_registry=get_prompt_registry(),
        template_selector=get_template_selector(),
        prompt_builder=get_prompt_builder(),
        cost_estimator=get_cost_estimator(),
        default_model=resolve_default_ai_model(settings),
    )


@lru_cache
def get_radiology_interpretation_ai_facade() -> RadiologyInterpretationAIFacade:
    generator = get_radiology_interpretation_generator()
    generate_use_case = InterpretRadiologyReportUseCase(
        generator=generator,
        parser=get_output_parser(),
        validator=get_result_validator(),
        finding_extraction_service=get_finding_extraction_service(),
        critical_finding_service=get_critical_finding_service(),
        recommendation_service=get_recommendation_service(),
        medical_reasoning=get_medical_reasoning_ai_facade(),
        audit_logger=get_radiology_interpretation_audit_logger(),
    )
    return RadiologyInterpretationAIFacade(
        generate_use_case=generate_use_case,
        finding_extraction_service=get_finding_extraction_service(),
        summary_service=get_summary_service(),
        generator=generator,
    )
