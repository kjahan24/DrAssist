"""Module composition root for the AI Lab Interpretation module.

Scope note — this task builds a **generation-only, interpretation-only**
module: it produces a structured `LabInterpretationResult` from explicit
laboratory values and clinical context, and never provides a definitive
diagnosis, persists results, or replaces physician judgment. Owns no
database session or per-request state, so every component here is
process-lifetime and exposed as an `lru_cache`d singleton, the same shape
every prior AI module's own `container.py` uses for itself.

**Genuine reuse of `app.modules.medical_reasoning_ai`** — this task's own
REUSE section names "Medical Reasoning Engine" explicitly, and unlike
every module built before it (phases 4.5-4.8, all of which predate that
module and so could only reuse its *architectural pattern*, never its
code — see e.g. `app.modules.differential_diagnosis_ai.container`'s own
REUSE discussion), `app.modules.medical_reasoning_ai` now actually exists
and was purpose-built (its own GOAL section: "the reusable reasoning
layer used by... Future AI modules") for exactly this situation: this
module is such a future module. `application/use_cases
/interpret_lab_results.py::InterpretLabResultsUseCase` therefore depends
directly on that peer module's own public port,
`app.modules.medical_reasoning_ai.public.interfaces.MedicalReasoningAIPort`,
constructed here via that peer module's own `container.py
.get_medical_reasoning_ai_facade` — the same "import a peer module's
`public/` package, plus its `container.py` factory function to construct
one" precedent every module in this codebase already uses for AI
Foundation's own `get_ai_gateway_facade`/`get_prompt_registry`. This is
not a violation of "never modify completed backend modules" — nothing in
`app.modules.medical_reasoning_ai` is modified; it is *consumed* through
the exact seam its own `public/interfaces.py` module docstring names for
this purpose. Specifically, `score_confidence` backs this module's own
confidence-scoring enrichment step (see that use case's own module
docstring) — `weight_evidence` is not used here, since this module's own
`LabFinding`/evidence-as-plain-strings shape has no `EvidenceItem`-typed
collection to hand it, and converting one just to call an otherwise-
unneeded method would be reuse for its own sake rather than a genuine
fit.

REUSE, for everything else, is satisfied exactly as it was for
`app.modules.medical_reasoning_ai` (see that module's own `container.py`
scope note for the identical reasoning): (1) AI Foundation directly
(`AIGatewayPort`, `PromptRegistry`), and (2) the genuinely module-
agnostic mechanics in `app.shared.infrastructure.text_processing` (JSON
extraction, placeholder detection, word-chunked streaming). "Shared
renderer" is satisfied by `application/services
/lab_interpretation_renderer.LabInterpretationRenderer` following the
identical JSON/Markdown/text rendering shape every prior AI module's own
renderer already established. "Shared audit infrastructure" is likewise
the `structlog`-via-`app.core.logging.get_logger` pattern every prior AI
module's own audit logger already uses. Provider selection, cost
estimation, and template registration remain this module's own small,
locally-owned copies for the same reason
`app.shared.infrastructure.text_processing`'s own module docstrings give:
they need AI Foundation's own types, and `app/shared/` may never import
from `app/modules/`.
"""

from functools import lru_cache

from app.core.config import get_settings
from app.modules.ai.container import get_ai_gateway_facade, get_prompt_registry
from app.modules.lab_interpretation_ai.application.ports import (
    CostEstimatorPort,
    CriticalValueAnalyzerPort,
    LabInterpretationAuditLoggerPort,
    LabInterpretationParserPort,
    LabInterpretationTemplateSelectorPort,
    LabInterpretationValidatorPort,
    LabInterpreterPort,
    LabPromptBuilderPort,
)
from app.modules.lab_interpretation_ai.application.services.critical_value_detection_service import (  # noqa: E501
    CriticalValueDetectionService,
)
from app.modules.lab_interpretation_ai.application.services.lab_interpretation_renderer import (
    LabInterpretationRenderer,
)
from app.modules.lab_interpretation_ai.application.services.lab_recommendation_service import (
    LabRecommendationService,
)
from app.modules.lab_interpretation_ai.application.services.lab_trend_analysis_service import (
    LabTrendAnalysisService,
)
from app.modules.lab_interpretation_ai.application.use_cases.interpret_lab_results import (
    InterpretLabResultsUseCase,
)
from app.modules.lab_interpretation_ai.infrastructure.audit.audit_logger import (
    StructlogLabInterpretationAuditLogger,
)
from app.modules.lab_interpretation_ai.infrastructure.cost.cost_estimator import CostEstimator
from app.modules.lab_interpretation_ai.infrastructure.critical_values.static_critical_value_analyzer import (  # noqa: E501
    StaticCriticalValueAnalyzer,
)
from app.modules.lab_interpretation_ai.infrastructure.generation.lab_interpretation_generator import (  # noqa: E501
    DefaultLabInterpretationGenerator,
)
from app.modules.lab_interpretation_ai.infrastructure.parsing.lab_interpretation_parser import (
    DefaultLabInterpretationParser,
)
from app.modules.lab_interpretation_ai.infrastructure.prompts.prompt_builder import (
    DefaultLabPromptBuilder,
)
from app.modules.lab_interpretation_ai.infrastructure.prompts.template_selector import (
    DefaultLabInterpretationTemplateSelector,
)
from app.modules.lab_interpretation_ai.infrastructure.provider_selection import (
    resolve_default_ai_model,
)
from app.modules.lab_interpretation_ai.infrastructure.validation.lab_interpretation_validator import (  # noqa: E501
    DefaultLabInterpretationValidator,
)
from app.modules.lab_interpretation_ai.public.facade import LabInterpretationAIFacade
from app.modules.medical_reasoning_ai.container import get_medical_reasoning_ai_facade


@lru_cache
def get_output_parser() -> LabInterpretationParserPort:
    return DefaultLabInterpretationParser()


@lru_cache
def get_critical_value_analyzer() -> CriticalValueAnalyzerPort:
    return StaticCriticalValueAnalyzer()


@lru_cache
def get_critical_value_service() -> CriticalValueDetectionService:
    return CriticalValueDetectionService(analyzer=get_critical_value_analyzer())


@lru_cache
def get_trend_service() -> LabTrendAnalysisService:
    return LabTrendAnalysisService()


@lru_cache
def get_recommendation_service() -> LabRecommendationService:
    return LabRecommendationService()


@lru_cache
def get_renderer() -> LabInterpretationRenderer:
    return LabInterpretationRenderer()


@lru_cache
def get_result_validator() -> LabInterpretationValidatorPort:
    return DefaultLabInterpretationValidator()


@lru_cache
def get_lab_interpretation_audit_logger() -> LabInterpretationAuditLoggerPort:
    return StructlogLabInterpretationAuditLogger()


@lru_cache
def get_cost_estimator() -> CostEstimatorPort:
    return CostEstimator()


@lru_cache
def get_template_selector() -> LabInterpretationTemplateSelectorPort:
    return DefaultLabInterpretationTemplateSelector()


@lru_cache
def get_prompt_builder() -> LabPromptBuilderPort:
    return DefaultLabPromptBuilder(ai_gateway=get_ai_gateway_facade())


@lru_cache
def get_lab_interpretation_generator() -> LabInterpreterPort:
    settings = get_settings()
    return DefaultLabInterpretationGenerator(
        ai_gateway=get_ai_gateway_facade(),
        prompt_registry=get_prompt_registry(),
        template_selector=get_template_selector(),
        prompt_builder=get_prompt_builder(),
        cost_estimator=get_cost_estimator(),
        default_model=resolve_default_ai_model(settings),
    )


@lru_cache
def get_lab_interpretation_ai_facade() -> LabInterpretationAIFacade:
    generator = get_lab_interpretation_generator()
    generate_use_case = InterpretLabResultsUseCase(
        generator=generator,
        parser=get_output_parser(),
        validator=get_result_validator(),
        critical_value_service=get_critical_value_service(),
        trend_service=get_trend_service(),
        recommendation_service=get_recommendation_service(),
        medical_reasoning=get_medical_reasoning_ai_facade(),
        audit_logger=get_lab_interpretation_audit_logger(),
    )
    return LabInterpretationAIFacade(
        generate_use_case=generate_use_case,
        renderer=get_renderer(),
        generator=generator,
    )
