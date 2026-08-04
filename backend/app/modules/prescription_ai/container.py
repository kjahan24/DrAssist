"""Module composition root for AI Prescription Assistance.

Scope note — this task builds a **generation-only** module: it drafts
`MedicationSuggestion`s from explicit clinical context and never
persists, issues, or replaces physician judgment on anything — "It NEVER
issues a prescription. It NEVER saves prescriptions. It NEVER replaces
physician judgment. Every output is a draft requiring physician review."
The pre-existing `app.modules.prescriptions` module (structured,
persisted prescription records — a completed backend module, not
modified by this task) is the expected future consumer of this one's
`public/interfaces.py::PrescriptionAIPort` for AI-assisted drafting; this
module owns no overlap with its tables. Prompt template names are
deliberately prefixed `prescription_suggestion`, not `prescriptions`, to
avoid any reader confusing an AI-Foundation `PromptRegistry` string key
with that unrelated sibling module — see `infrastructure/prompts
/templates.py`'s own docstring, and `app.modules.icd10_ai.container`'s
identical precedent relative to `app.modules.icd10_coding`.

REUSE, per this task's own section — "AI Foundation, AI Clinical
Copilot, AI Clinical Note AI, AI SOAP Note AI, AI ICD-10 AI, Shared
prompt framework, Shared parser framework, Shared validation framework,
Shared streaming framework": the module-independence rule ("modules may
only import each other's `public/` package") does not relax because a
task's REUSE wording is broader than a prior phase's — it is satisfied
here exactly as it was for `app.modules.icd10_ai` (see that module's own
`container.py` scope note for the identical reasoning applied to its own
REUSE section): (1) AI Foundation directly (`AIGatewayPort`,
`PromptRegistry`), and (2) the genuinely module-agnostic mechanics in
`app.shared.infrastructure.text_processing` (JSON extraction, placeholder
detection, word-chunked streaming). Inspecting `ai_copilot`'s,
`clinical_note_ai`'s, `soap_note_ai`'s, and `icd10_ai`'s own `public/`
surfaces confirms none of them expose anything prescription-relevant to
import (their public contracts are about copilot orchestration, clinical
notes, SOAP notes, and ICD-10 suggestions respectively, not shared
parsing/validation utilities) — so, as with `icd10_ai`, the only
remaining form of "reuse" available is following the identical
architectural PATTERN those modules already established (template
registrar idiom, cost estimator shape, provider selection shape, audit
logger shape, knowledge-port "structural gate vs. soft signal" split),
not importing their internals. Provider selection, cost estimation, and
template registration remain this module's own small, locally-owned
copies for the same reason `app.shared.infrastructure.text_processing`'s
own module docstrings give: they need AI Foundation's own types, and
`app/shared/` may never import from `app/modules/`.

This module's input is fully self-contained clinical context (chief
complaint, HPI, symptoms, ROS, exam, vitals, assessment, plan, clinical/
SOAP note text, ICD-10 suggestions as plain text, existing medications,
allergies, medical conditions, lab results), not an
`app.modules.ai_copilot`-style patient-history lookup — the same
"explicit encounter input only" design `app.modules.clinical_note_ai`/
`app.modules.soap_note_ai`/`app.modules.icd10_ai` all use for themselves.

Owns no database session or per-request state (see the above — no
persistence at all), so every component here is process-lifetime and
exposed as an `lru_cache`d singleton, the same shape
`app.modules.icd10_ai.container` uses for itself.
"""

from functools import lru_cache

from app.core.config import get_settings
from app.modules.ai.container import get_ai_gateway_facade, get_prompt_registry
from app.modules.prescription_ai.application.ports import (
    CostEstimatorPort,
    DrugInteractionPort,
    MedicationKnowledgePort,
    PrescriptionAuditLoggerPort,
    PrescriptionGeneratorPort,
    PrescriptionPromptBuilderPort,
    PrescriptionSuggestionParserPort,
    PrescriptionSuggestionValidatorPort,
    PrescriptionTemplateSelectorPort,
)
from app.modules.prescription_ai.application.services.medication_safety_analysis_service import (
    MedicationSafetyAnalysisService,
)
from app.modules.prescription_ai.application.services.prescription_suggestion_renderer import (
    PrescriptionSuggestionRenderer,
)
from app.modules.prescription_ai.application.use_cases.analyze_medication_safety import (
    AnalyzeMedicationSafetyUseCase,
)
from app.modules.prescription_ai.application.use_cases.generate_prescription_suggestion import (
    GeneratePrescriptionSuggestionUseCase,
)
from app.modules.prescription_ai.application.use_cases.validate_prescription_context import (
    ValidatePrescriptionContextUseCase,
)
from app.modules.prescription_ai.infrastructure.audit.audit_logger import (
    StructlogPrescriptionAuditLogger,
)
from app.modules.prescription_ai.infrastructure.cost.cost_estimator import CostEstimator
from app.modules.prescription_ai.infrastructure.generation.prescription_generator import (
    DefaultPrescriptionGenerator,
)
from app.modules.prescription_ai.infrastructure.interactions.drug_interaction_checker import (
    StaticDrugInteractionChecker,
)
from app.modules.prescription_ai.infrastructure.knowledge.medication_knowledge_base import (
    StaticMedicationKnowledgeBase,
)
from app.modules.prescription_ai.infrastructure.parsing.prescription_suggestion_parser import (
    DefaultPrescriptionSuggestionParser,
)
from app.modules.prescription_ai.infrastructure.prompts.prompt_builder import (
    DefaultPrescriptionPromptBuilder,
)
from app.modules.prescription_ai.infrastructure.prompts.template_selector import (
    DefaultPrescriptionTemplateSelector,
)
from app.modules.prescription_ai.infrastructure.provider_selection import resolve_default_ai_model
from app.modules.prescription_ai.infrastructure.validation import (
    prescription_suggestion_validator,
)
from app.modules.prescription_ai.public.facade import PrescriptionAIFacade


@lru_cache
def get_output_parser() -> PrescriptionSuggestionParserPort:
    return DefaultPrescriptionSuggestionParser()


@lru_cache
def get_medication_knowledge_base() -> MedicationKnowledgePort:
    return StaticMedicationKnowledgeBase()


@lru_cache
def get_drug_interaction_checker() -> DrugInteractionPort:
    return StaticDrugInteractionChecker()


@lru_cache
def get_suggestion_validator() -> PrescriptionSuggestionValidatorPort:
    return prescription_suggestion_validator.DefaultPrescriptionSuggestionValidator()


@lru_cache
def get_prescription_audit_logger() -> PrescriptionAuditLoggerPort:
    return StructlogPrescriptionAuditLogger()


@lru_cache
def get_cost_estimator() -> CostEstimatorPort:
    return CostEstimator()


@lru_cache
def get_template_selector() -> PrescriptionTemplateSelectorPort:
    return DefaultPrescriptionTemplateSelector()


@lru_cache
def get_prompt_builder() -> PrescriptionPromptBuilderPort:
    return DefaultPrescriptionPromptBuilder(ai_gateway=get_ai_gateway_facade())


@lru_cache
def get_safety_analysis_service() -> MedicationSafetyAnalysisService:
    return MedicationSafetyAnalysisService(
        drug_interaction=get_drug_interaction_checker(),
        knowledge=get_medication_knowledge_base(),
    )


@lru_cache
def get_suggestion_renderer() -> PrescriptionSuggestionRenderer:
    return PrescriptionSuggestionRenderer()


@lru_cache
def get_prescription_generator() -> PrescriptionGeneratorPort:
    settings = get_settings()
    return DefaultPrescriptionGenerator(
        ai_gateway=get_ai_gateway_facade(),
        prompt_registry=get_prompt_registry(),
        template_selector=get_template_selector(),
        prompt_builder=get_prompt_builder(),
        cost_estimator=get_cost_estimator(),
        default_model=resolve_default_ai_model(settings),
    )


@lru_cache
def get_prescription_ai_facade() -> PrescriptionAIFacade:
    generator = get_prescription_generator()
    generate_use_case = GeneratePrescriptionSuggestionUseCase(
        generator=generator,
        parser=get_output_parser(),
        validator=get_suggestion_validator(),
        safety_service=get_safety_analysis_service(),
        audit_logger=get_prescription_audit_logger(),
    )
    validate_use_case = ValidatePrescriptionContextUseCase()
    analyze_safety_use_case = AnalyzeMedicationSafetyUseCase(
        safety_service=get_safety_analysis_service()
    )
    return PrescriptionAIFacade(
        generate_use_case=generate_use_case,
        validate_use_case=validate_use_case,
        analyze_safety_use_case=analyze_safety_use_case,
        renderer=get_suggestion_renderer(),
        generator=generator,
    )
