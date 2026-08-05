"""Module composition root for the AI Drug Interaction & Medication
Safety module.

Scope note — this task builds a **generation-only, decision-support-
only** module: it analyzes a caller-supplied medication list and
produces a structured `DrugInteractionAnalysisResult`, and never
autonomously prescribes medication, persists anything, or replaces
physician judgment. Owns no database session or per-request state, so
every component here is process-lifetime and exposed as an `lru_cache`d
singleton, the same shape every prior AI module's own `container.py`
uses for itself.

**Genuine reuse of `app.modules.medical_reasoning_ai`** — this task's
own REUSE section names "Medical Reasoning AI" explicitly.
`application/use_cases/analyze_medication_safety.py
::AnalyzeMedicationSafetyUseCase` depends directly on that peer module's
own public port,
`app.modules.medical_reasoning_ai.public.interfaces.MedicalReasoningAIPort`,
constructed here via that peer module's own `container.py
.get_medical_reasoning_ai_facade` — the exact same "import a peer
module's `public/` package, plus its `container.py` factory function to
construct one" precedent every prior interpretation-AI module's own
`container.py` already establishes for itself: `score_confidence` backs
this module's own confidence-scoring enrichment step, using
`len(deduped_interactions)` as the `supporting_count` — the closest
analog this module's own interaction-based OUTPUT has to that port's
generic "supporting evidence" concept.

**Why `app.modules.prescription_ai` is not called into directly** —
this task's own REUSE section names "Prescription AI" explicitly, and
unlike every other reused module, `app.modules.prescription_ai.public
.interfaces.PrescriptionAIPort` genuinely does expose a standalone,
directly-relevant-sounding capability:
`analyze_medication_safety(suggestion_set, *, existing_medications,
allergies)`. It was investigated specifically for this reason. It is not
called into: `suggestion_set` must be a
`app.modules.prescription_ai.public.dto.PrescriptionSuggestionSet`,
whose own `MedicationSuggestion` items require `strength`, `quantity`,
`is_prn`, and a prescription_ai-specific `AdministrationRoute` enum —
fields this module's own generic `MedicationEntry` (`drug_name`,
`generic_name`, `brand_name`, `dose`, `frequency`, `route`, `duration`,
per this task's own SUPPORTED INPUT section) neither collects nor needs.
Constructing one from the other would mean *fabricating* data this
module was never given (a quantity, a PRN flag, a specific enum route)
just to satisfy an unrelated module's own generation-result shape — the
same failure mode `docs/backend-architecture/10_module_communication.md`
warns a forced integration produces, worse than not reusing at all. This
module therefore reuses `app.modules.prescription_ai` the same way every
prior AI module reuses its own non-`medical_reasoning_ai` peers: the
architectural *pattern*, not the code, the same "reuse the pattern, not
the code" conclusion reached for the AI Clinical Copilot/Clinical Note
AI/SOAP Note AI/ICD-10 AI/Differential Diagnosis AI/Lab Interpretation
AI/Radiology Interpretation AI/Pathology Interpretation AI modules
throughout every prior phase.

REUSE, for everything else, is satisfied exactly as it was for
`app.modules.pathology_interpretation_ai` (see that module's own
`container.py` scope note for the identical reasoning): (1) AI
Foundation directly (`AIGatewayPort`, `PromptRegistry`), and (2) the
genuinely module-agnostic mechanics in `app.shared.infrastructure
.text_processing` (JSON extraction, placeholder detection, word-chunked
streaming). "Shared renderer" is satisfied by `application/services
/drug_safety_report_renderer.DrugSafetyReportRenderer` following the
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
from app.modules.drug_interaction_ai.application.ports import (
    CostEstimatorPort,
    DoseAdjustmentPort,
    DrugInteractionPort,
    DrugSafetyAnalysisAuditLoggerPort,
    DrugSafetyAnalysisGeneratorPort,
    DrugSafetyAnalysisParserPort,
    DrugSafetyAnalysisPromptBuilderPort,
    DrugSafetyAnalysisTemplateSelectorPort,
    DrugSafetyAnalysisValidatorPort,
    InteractionEvidencePort,
    MedicationSafetyPort,
)
from app.modules.drug_interaction_ai.application.services.alternative_medication_service import (
    AlternativeMedicationService,
)
from app.modules.drug_interaction_ai.application.services.contraindication_service import (
    ContraindicationService,
)
from app.modules.drug_interaction_ai.application.services.dose_adjustment_service import (
    DoseAdjustmentService,
)
from app.modules.drug_interaction_ai.application.services.drug_interaction_service import (
    DrugInteractionService,
)
from app.modules.drug_interaction_ai.application.services.drug_safety_report_renderer import (
    DrugSafetyReportRenderer,
)
from app.modules.drug_interaction_ai.application.services.medication_safety_service import (
    MedicationSafetyService,
)
from app.modules.drug_interaction_ai.application.use_cases.analyze_medication_safety import (
    AnalyzeMedicationSafetyUseCase,
)
from app.modules.drug_interaction_ai.infrastructure.audit.audit_logger import (
    StructlogDrugSafetyAnalysisAuditLogger,
)
from app.modules.drug_interaction_ai.infrastructure.cost.cost_estimator import CostEstimator
from app.modules.drug_interaction_ai.infrastructure.dose_adjustment.static_dose_adjustment_knowledge_base import (  # noqa: E501
    StaticDoseAdjustmentKnowledgeBase,
)
from app.modules.drug_interaction_ai.infrastructure.generation.drug_safety_analysis_generator import (  # noqa: E501
    DefaultDrugSafetyAnalysisGenerator,
)
from app.modules.drug_interaction_ai.infrastructure.interaction_knowledge.static_drug_interaction_knowledge_base import (  # noqa: E501
    StaticDrugInteractionKnowledgeBase,
    StaticInteractionEvidenceKnowledgeBase,
)
from app.modules.drug_interaction_ai.infrastructure.medication_safety.static_medication_safety_knowledge_base import (  # noqa: E501
    StaticMedicationSafetyKnowledgeBase,
)
from app.modules.drug_interaction_ai.infrastructure.parsing.drug_safety_analysis_parser import (
    DefaultDrugSafetyAnalysisParser,
)
from app.modules.drug_interaction_ai.infrastructure.prompts.prompt_builder import (
    DefaultDrugSafetyAnalysisPromptBuilder,
)
from app.modules.drug_interaction_ai.infrastructure.prompts.template_selector import (
    DefaultDrugSafetyAnalysisTemplateSelector,
)
from app.modules.drug_interaction_ai.infrastructure.provider_selection import (
    resolve_default_ai_model,
)
from app.modules.drug_interaction_ai.infrastructure.validation.drug_safety_analysis_validator import (  # noqa: E501
    DefaultDrugSafetyAnalysisValidator,
)
from app.modules.drug_interaction_ai.public.facade import DrugInteractionAIFacade
from app.modules.medical_reasoning_ai.container import get_medical_reasoning_ai_facade


@lru_cache
def get_output_parser() -> DrugSafetyAnalysisParserPort:
    return DefaultDrugSafetyAnalysisParser()


@lru_cache
def get_drug_interaction_port() -> DrugInteractionPort:
    return StaticDrugInteractionKnowledgeBase()


@lru_cache
def get_interaction_evidence_port() -> InteractionEvidencePort:
    return StaticInteractionEvidenceKnowledgeBase()


@lru_cache
def get_medication_safety_port() -> MedicationSafetyPort:
    return StaticMedicationSafetyKnowledgeBase()


@lru_cache
def get_dose_adjustment_port() -> DoseAdjustmentPort:
    return StaticDoseAdjustmentKnowledgeBase()


@lru_cache
def get_drug_interaction_service() -> DrugInteractionService:
    return DrugInteractionService(
        interaction_port=get_drug_interaction_port(),
        evidence_port=get_interaction_evidence_port(),
    )


@lru_cache
def get_medication_safety_service() -> MedicationSafetyService:
    return MedicationSafetyService(port=get_medication_safety_port())


@lru_cache
def get_contraindication_service() -> ContraindicationService:
    return ContraindicationService(port=get_medication_safety_port())


@lru_cache
def get_dose_adjustment_service() -> DoseAdjustmentService:
    return DoseAdjustmentService(port=get_dose_adjustment_port())


@lru_cache
def get_alternative_medication_service() -> AlternativeMedicationService:
    return AlternativeMedicationService()


@lru_cache
def get_renderer() -> DrugSafetyReportRenderer:
    return DrugSafetyReportRenderer()


@lru_cache
def get_result_validator() -> DrugSafetyAnalysisValidatorPort:
    return DefaultDrugSafetyAnalysisValidator()


@lru_cache
def get_drug_interaction_audit_logger() -> DrugSafetyAnalysisAuditLoggerPort:
    return StructlogDrugSafetyAnalysisAuditLogger()


@lru_cache
def get_cost_estimator() -> CostEstimatorPort:
    return CostEstimator()


@lru_cache
def get_template_selector() -> DrugSafetyAnalysisTemplateSelectorPort:
    return DefaultDrugSafetyAnalysisTemplateSelector()


@lru_cache
def get_prompt_builder() -> DrugSafetyAnalysisPromptBuilderPort:
    return DefaultDrugSafetyAnalysisPromptBuilder(ai_gateway=get_ai_gateway_facade())


@lru_cache
def get_drug_interaction_generator() -> DrugSafetyAnalysisGeneratorPort:
    settings = get_settings()
    return DefaultDrugSafetyAnalysisGenerator(
        ai_gateway=get_ai_gateway_facade(),
        prompt_registry=get_prompt_registry(),
        template_selector=get_template_selector(),
        prompt_builder=get_prompt_builder(),
        cost_estimator=get_cost_estimator(),
        default_model=resolve_default_ai_model(settings),
    )


@lru_cache
def get_drug_interaction_ai_facade() -> DrugInteractionAIFacade:
    generator = get_drug_interaction_generator()
    analyze_use_case = AnalyzeMedicationSafetyUseCase(
        generator=generator,
        parser=get_output_parser(),
        validator=get_result_validator(),
        drug_interaction_service=get_drug_interaction_service(),
        medication_safety_service=get_medication_safety_service(),
        contraindication_service=get_contraindication_service(),
        dose_adjustment_service=get_dose_adjustment_service(),
        alternative_medication_service=get_alternative_medication_service(),
        medical_reasoning=get_medical_reasoning_ai_facade(),
        audit_logger=get_drug_interaction_audit_logger(),
    )
    return DrugInteractionAIFacade(
        analyze_use_case=analyze_use_case,
        renderer=get_renderer(),
        generator=generator,
    )
