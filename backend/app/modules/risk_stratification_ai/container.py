"""Module composition root for the AI Risk Stratification & Early
Warning Score module.

Scope note — this task builds a **generation-only, decision-support-
only** module: it analyzes caller-supplied vital signs/laboratory
values/clinical context and produces a structured
`RiskStratificationResult`, and never autonomously makes medical
decisions, persists anything, or replaces physician judgment. Owns no
database session or per-request state, so every component here is
process-lifetime and exposed as an `lru_cache`d singleton, the same
shape every prior AI module's own `container.py` uses for itself.

**Genuine reuse of `app.modules.medical_reasoning_ai`** — this task's
own REUSE section names "Medical Reasoning" among its own SUPPORTED
INPUT list, and this module reuses `app.modules.medical_reasoning_ai`
the same genuine way every interpretation-AI module since Phase 4.9 has:
`application/use_cases/analyze_patient_risk.py
::AnalyzePatientRiskUseCase` depends directly on that peer module's own
public port,
`app.modules.medical_reasoning_ai.public.interfaces.MedicalReasoningAIPort`,
constructed here via that peer module's own `container.py
.get_medical_reasoning_ai_facade` — the exact same "import a peer
module's `public/` package, plus its `container.py` factory function to
construct one" precedent every prior interpretation-AI module's own
`container.py` already establishes for itself: `score_confidence` backs
this module's own confidence-scoring enrichment step, using
`len(merged_scores)` as the `supporting_count` — the closest analog this
module's own risk-score-based OUTPUT has to that port's generic
"supporting evidence" concept.

**Why `app.modules.lab_interpretation_ai`/`radiology_interpretation_ai`/
`pathology_interpretation_ai` are not called into directly** — this
task's own SUPPORTED INPUT section names "Laboratory Interpretation,
Radiology Interpretation, Pathology Interpretation" explicitly, alongside
"Medical Reasoning". Unlike `MedicalReasoningAIPort.score_confidence`
(a small, primitive-typed, use-case-level capability this module
directly needs), those three peer modules' own public ports each expose
only a full `generate_*`/`interpret_*` **generation pipeline** of their
own — accepting *their own* structured input value objects (lab
values/radiology report text/pathology report text) and producing
*their own* `Generated*` results, not a lookup this module could call
mid-pipeline. Calling into any of the three here would mean this module
either re-running an entire sibling generation pipeline itself (a
second, redundant AI call and a second audit trail this task's own
SUPPORTED INPUT list does not ask for) or fabricating that sibling
module's own structured input from data this module was never given.
This task's own wording — "Laboratory Interpretation, Radiology
Interpretation, Pathology Interpretation" listed as plain SUPPORTED
INPUT items, exactly alongside "Clinical Notes"/"SOAP Notes" — reads as
"accept an already-generated summary as context", not "generate one
yourself"; `domain/value_objects.py::RiskStratificationInput` therefore
models all three as plain `str | None` fields the caller populates with
whatever summary text it already has (e.g. a prior call to that peer
module's own facade), the same "explicit input, not a live cross-module
lookup" design every prior AI module's own peer-module context fields
establish for themselves.

REUSE, for everything else, is satisfied exactly as it was for
`app.modules.drug_interaction_ai` (see that module's own `container.py`
scope note for the identical reasoning): (1) AI Foundation directly
(`AIGatewayPort`, `PromptRegistry`), and (2) the genuinely
module-agnostic mechanics in `app.shared.infrastructure.text_processing`
(JSON extraction, placeholder detection, word-chunked streaming).
"Shared renderer" is satisfied by `application/services
/risk_report_renderer.RiskReportRenderer` following the identical
JSON/Markdown/text rendering shape every prior AI module's own renderer
already established. "Shared audit infrastructure" is likewise the
`structlog`-via-`app.core.logging.get_logger` pattern every prior AI
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
from app.modules.risk_stratification_ai.application.ports import (
    ClinicalRiskPort,
    CostEstimatorPort,
    EarlyWarningPort,
    RiskScoringPort,
    RiskStratificationAnalysisAuditLoggerPort,
    RiskStratificationAnalysisGeneratorPort,
    RiskStratificationAnalysisParserPort,
    RiskStratificationAnalysisPromptBuilderPort,
    RiskStratificationAnalysisTemplateSelectorPort,
    RiskStratificationAnalysisValidatorPort,
)
from app.modules.risk_stratification_ai.application.services.clinical_risk_assessment_service import (  # noqa: E501
    ClinicalRiskAssessmentService,
)
from app.modules.risk_stratification_ai.application.services.early_warning_service import (
    EarlyWarningService,
)
from app.modules.risk_stratification_ai.application.services.monitoring_recommendation_service import (  # noqa: E501
    MonitoringRecommendationService,
)
from app.modules.risk_stratification_ai.application.services.risk_explanation_service import (
    RiskExplanationService,
)
from app.modules.risk_stratification_ai.application.services.risk_report_renderer import (
    RiskReportRenderer,
)
from app.modules.risk_stratification_ai.application.services.risk_scoring_service import (
    RiskScoringService,
)
from app.modules.risk_stratification_ai.application.use_cases.analyze_patient_risk import (
    AnalyzePatientRiskUseCase,
)
from app.modules.risk_stratification_ai.infrastructure.audit.audit_logger import (
    StructlogRiskStratificationAuditLogger,
)
from app.modules.risk_stratification_ai.infrastructure.clinical_risk.static_clinical_risk_knowledge_base import (  # noqa: E501
    StaticClinicalRiskKnowledgeBase,
)
from app.modules.risk_stratification_ai.infrastructure.clinical_scoring.standard_risk_scoring_calculator import (  # noqa: E501
    StandardRiskScoringCalculator,
)
from app.modules.risk_stratification_ai.infrastructure.cost.cost_estimator import CostEstimator
from app.modules.risk_stratification_ai.infrastructure.early_warning.standard_early_warning_analyzer import (  # noqa: E501
    StandardEarlyWarningAnalyzer,
)
from app.modules.risk_stratification_ai.infrastructure.generation.risk_stratification_generator import (  # noqa: E501
    DefaultRiskStratificationAnalysisGenerator,
)
from app.modules.risk_stratification_ai.infrastructure.parsing.risk_stratification_parser import (
    DefaultRiskStratificationAnalysisParser,
)
from app.modules.risk_stratification_ai.infrastructure.prompts.prompt_builder import (
    DefaultRiskStratificationAnalysisPromptBuilder,
)
from app.modules.risk_stratification_ai.infrastructure.prompts.template_selector import (
    DefaultRiskStratificationAnalysisTemplateSelector,
)
from app.modules.risk_stratification_ai.infrastructure.provider_selection import (
    resolve_default_ai_model,
)
from app.modules.risk_stratification_ai.infrastructure.validation.risk_stratification_validator import (  # noqa: E501
    DefaultRiskStratificationAnalysisValidator,
)
from app.modules.risk_stratification_ai.public.facade import RiskStratificationAIFacade


@lru_cache
def get_output_parser() -> RiskStratificationAnalysisParserPort:
    return DefaultRiskStratificationAnalysisParser()


@lru_cache
def get_risk_scoring_port() -> RiskScoringPort:
    return StandardRiskScoringCalculator()


@lru_cache
def get_early_warning_port() -> EarlyWarningPort:
    return StandardEarlyWarningAnalyzer()


@lru_cache
def get_clinical_risk_port() -> ClinicalRiskPort:
    return StaticClinicalRiskKnowledgeBase()


@lru_cache
def get_risk_scoring_service() -> RiskScoringService:
    return RiskScoringService(scoring_port=get_risk_scoring_port())


@lru_cache
def get_clinical_risk_assessment_service() -> ClinicalRiskAssessmentService:
    return ClinicalRiskAssessmentService(clinical_risk_port=get_clinical_risk_port())


@lru_cache
def get_early_warning_service() -> EarlyWarningService:
    return EarlyWarningService(early_warning_port=get_early_warning_port())


@lru_cache
def get_risk_explanation_service() -> RiskExplanationService:
    return RiskExplanationService()


@lru_cache
def get_monitoring_recommendation_service() -> MonitoringRecommendationService:
    return MonitoringRecommendationService(early_warning_port=get_early_warning_port())


@lru_cache
def get_renderer() -> RiskReportRenderer:
    return RiskReportRenderer()


@lru_cache
def get_result_validator() -> RiskStratificationAnalysisValidatorPort:
    return DefaultRiskStratificationAnalysisValidator()


@lru_cache
def get_risk_stratification_audit_logger() -> RiskStratificationAnalysisAuditLoggerPort:
    return StructlogRiskStratificationAuditLogger()


@lru_cache
def get_cost_estimator() -> CostEstimatorPort:
    return CostEstimator()


@lru_cache
def get_template_selector() -> RiskStratificationAnalysisTemplateSelectorPort:
    return DefaultRiskStratificationAnalysisTemplateSelector()


@lru_cache
def get_prompt_builder() -> RiskStratificationAnalysisPromptBuilderPort:
    return DefaultRiskStratificationAnalysisPromptBuilder(ai_gateway=get_ai_gateway_facade())


@lru_cache
def get_risk_stratification_generator() -> RiskStratificationAnalysisGeneratorPort:
    settings = get_settings()
    return DefaultRiskStratificationAnalysisGenerator(
        ai_gateway=get_ai_gateway_facade(),
        prompt_registry=get_prompt_registry(),
        template_selector=get_template_selector(),
        prompt_builder=get_prompt_builder(),
        cost_estimator=get_cost_estimator(),
        default_model=resolve_default_ai_model(settings),
    )


@lru_cache
def get_risk_stratification_ai_facade() -> RiskStratificationAIFacade:
    generator = get_risk_stratification_generator()
    analyze_use_case = AnalyzePatientRiskUseCase(
        generator=generator,
        parser=get_output_parser(),
        validator=get_result_validator(),
        risk_scoring_service=get_risk_scoring_service(),
        clinical_risk_assessment_service=get_clinical_risk_assessment_service(),
        early_warning_service=get_early_warning_service(),
        risk_explanation_service=get_risk_explanation_service(),
        monitoring_recommendation_service=get_monitoring_recommendation_service(),
        medical_reasoning=get_medical_reasoning_ai_facade(),
        audit_logger=get_risk_stratification_audit_logger(),
    )
    return RiskStratificationAIFacade(
        analyze_use_case=analyze_use_case,
        renderer=get_renderer(),
        generator=generator,
    )
