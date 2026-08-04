"""Module composition root for AI Differential Diagnosis.

Scope note — this task builds a **generation-only** module: it produces
a ranked `DifferentialDiagnosisResult` from explicit clinical evidence
and never persists, finalizes, or replaces physician judgment on
anything — "It NEVER creates a final diagnosis. It NEVER replaces
physician judgment. All outputs are clinical decision-support only."
The pre-existing `app.modules.differential_diagnosis` module
(structured, persisted differential diagnosis records — a completed
backend module, not modified by this task) is the expected future
consumer of this one's `public/interfaces.py
::DifferentialDiagnosisAIPort` for AI-assisted drafting; this module
owns no overlap with its tables. Prompt template names are deliberately
prefixed `differential_diagnosis_suggestion`, not
`differential_diagnosis`, to avoid any reader confusing an AI-Foundation
`PromptRegistry` string key with that unrelated sibling module — see
`infrastructure/prompts/templates.py`'s own docstring, and
`app.modules.icd10_ai.container`/`app.modules.prescription_ai.container`'s
identical precedent relative to their own sibling modules.

REUSE, per this task's own section — "AI Foundation, AI Clinical
Copilot, AI Clinical Note AI, AI SOAP Note AI, AI ICD-10 AI, AI
Prescription AI, Shared prompt framework, Shared parser framework,
Shared validation framework, Shared streaming framework": the module-
independence rule ("modules may only import each other's `public/`
package") does not relax because a task's REUSE wording is broader than
a prior phase's — it is satisfied here exactly as it was for
`app.modules.prescription_ai` (see that module's own `container.py`
scope note for the identical reasoning applied to its own REUSE
section): (1) AI Foundation directly (`AIGatewayPort`, `PromptRegistry`),
and (2) the genuinely module-agnostic mechanics in
`app.shared.infrastructure.text_processing` (JSON extraction, placeholder
detection, word-chunked streaming). Inspecting `ai_copilot`'s,
`clinical_note_ai`'s, `soap_note_ai`'s, `icd10_ai`'s, and
`prescription_ai`'s own `public/` surfaces confirms none of them expose
anything differential-diagnosis-relevant to import (their public
contracts are about copilot orchestration, clinical notes, SOAP notes,
ICD-10 suggestions, and prescription suggestions respectively, not
shared parsing/validation utilities) — so, as with those modules, the
only remaining form of "reuse" available is following the identical
architectural PATTERN they already established (template registrar
idiom, cost estimator shape, provider selection shape, audit logger
shape, deterministic-port-plus-service enrichment pattern), not
importing their internals. Provider selection, cost estimation, and
template registration remain this module's own small, locally-owned
copies for the same reason `app.shared.infrastructure.text_processing`'s
own module docstrings give: they need AI Foundation's own types, and
`app/shared/` may never import from `app/modules/`.

This module's input is fully self-contained clinical evidence (chief
complaint, HPI, symptoms, ROS, exam, vitals, labs, imaging, clinical/
SOAP note text, ICD-10 suggestions and prescription suggestions as plain
text, allergies, medical conditions), not an `app.modules.ai_copilot`-
style patient-history lookup — the same "explicit encounter input only"
design `app.modules.clinical_note_ai`/`app.modules.soap_note_ai`/
`app.modules.icd10_ai`/`app.modules.prescription_ai` all use for
themselves.

Owns no database session or per-request state (see the above — no
persistence at all), so every component here is process-lifetime and
exposed as an `lru_cache`d singleton, the same shape
`app.modules.prescription_ai.container` uses for itself.
"""

from functools import lru_cache

from app.core.config import get_settings
from app.modules.ai.container import get_ai_gateway_facade, get_prompt_registry
from app.modules.differential_diagnosis_ai.application.ports import (
    ClinicalReasoningPort,
    CostEstimatorPort,
    DifferentialDiagnosisAuditLoggerPort,
    DifferentialDiagnosisGeneratorPort,
    DifferentialDiagnosisParserPort,
    DifferentialDiagnosisPromptBuilderPort,
    DifferentialDiagnosisTemplateSelectorPort,
    DifferentialDiagnosisValidatorPort,
)
from app.modules.differential_diagnosis_ai.application.services.clinical_reasoning_service import (
    ClinicalReasoningService,
)
from app.modules.differential_diagnosis_ai.application.services.differential_diagnosis_ranking_service import (  # noqa: E501
    DifferentialDiagnosisRankingService,
)
from app.modules.differential_diagnosis_ai.application.services.differential_diagnosis_renderer import (  # noqa: E501
    DifferentialDiagnosisRenderer,
)
from app.modules.differential_diagnosis_ai.application.use_cases.generate_differential_diagnosis import (  # noqa: E501
    GenerateDifferentialDiagnosisUseCase,
)
from app.modules.differential_diagnosis_ai.application.use_cases.rank_differential_diagnosis import (  # noqa: E501
    RankDifferentialDiagnosisUseCase,
)
from app.modules.differential_diagnosis_ai.application.use_cases.validate_clinical_evidence import (  # noqa: E501
    ValidateClinicalEvidenceUseCase,
)
from app.modules.differential_diagnosis_ai.infrastructure.audit.audit_logger import (
    StructlogDifferentialDiagnosisAuditLogger,
)
from app.modules.differential_diagnosis_ai.infrastructure.cost.cost_estimator import CostEstimator
from app.modules.differential_diagnosis_ai.infrastructure.generation.differential_diagnosis_generator import (  # noqa: E501
    DefaultDifferentialDiagnosisGenerator,
)
from app.modules.differential_diagnosis_ai.infrastructure.parsing.differential_diagnosis_parser import (  # noqa: E501
    DefaultDifferentialDiagnosisParser,
)
from app.modules.differential_diagnosis_ai.infrastructure.prompts.prompt_builder import (
    DefaultDifferentialDiagnosisPromptBuilder,
)
from app.modules.differential_diagnosis_ai.infrastructure.prompts.template_selector import (
    DefaultDifferentialDiagnosisTemplateSelector,
)
from app.modules.differential_diagnosis_ai.infrastructure.provider_selection import (
    resolve_default_ai_model,
)
from app.modules.differential_diagnosis_ai.infrastructure.reasoning.clinical_reasoning_advisor import (  # noqa: E501
    DefaultClinicalReasoningAdvisor,
)
from app.modules.differential_diagnosis_ai.infrastructure.validation import (
    differential_diagnosis_validator,
)
from app.modules.differential_diagnosis_ai.public.facade import DifferentialDiagnosisAIFacade


@lru_cache
def get_output_parser() -> DifferentialDiagnosisParserPort:
    return DefaultDifferentialDiagnosisParser()


@lru_cache
def get_clinical_reasoning_advisor() -> ClinicalReasoningPort:
    return DefaultClinicalReasoningAdvisor()


@lru_cache
def get_result_validator() -> DifferentialDiagnosisValidatorPort:
    return differential_diagnosis_validator.DefaultDifferentialDiagnosisValidator()


@lru_cache
def get_differential_diagnosis_audit_logger() -> DifferentialDiagnosisAuditLoggerPort:
    return StructlogDifferentialDiagnosisAuditLogger()


@lru_cache
def get_cost_estimator() -> CostEstimatorPort:
    return CostEstimator()


@lru_cache
def get_template_selector() -> DifferentialDiagnosisTemplateSelectorPort:
    return DefaultDifferentialDiagnosisTemplateSelector()


@lru_cache
def get_prompt_builder() -> DifferentialDiagnosisPromptBuilderPort:
    return DefaultDifferentialDiagnosisPromptBuilder(ai_gateway=get_ai_gateway_facade())


@lru_cache
def get_reasoning_service() -> ClinicalReasoningService:
    return ClinicalReasoningService(reasoning=get_clinical_reasoning_advisor())


@lru_cache
def get_ranking_service() -> DifferentialDiagnosisRankingService:
    return DifferentialDiagnosisRankingService()


@lru_cache
def get_result_renderer() -> DifferentialDiagnosisRenderer:
    return DifferentialDiagnosisRenderer()


@lru_cache
def get_differential_diagnosis_generator() -> DifferentialDiagnosisGeneratorPort:
    settings = get_settings()
    return DefaultDifferentialDiagnosisGenerator(
        ai_gateway=get_ai_gateway_facade(),
        prompt_registry=get_prompt_registry(),
        template_selector=get_template_selector(),
        prompt_builder=get_prompt_builder(),
        cost_estimator=get_cost_estimator(),
        default_model=resolve_default_ai_model(settings),
    )


@lru_cache
def get_differential_diagnosis_ai_facade() -> DifferentialDiagnosisAIFacade:
    generator = get_differential_diagnosis_generator()
    generate_use_case = GenerateDifferentialDiagnosisUseCase(
        generator=generator,
        parser=get_output_parser(),
        validator=get_result_validator(),
        reasoning_service=get_reasoning_service(),
        ranking_service=get_ranking_service(),
        audit_logger=get_differential_diagnosis_audit_logger(),
    )
    rank_use_case = RankDifferentialDiagnosisUseCase(ranking_service=get_ranking_service())
    validate_use_case = ValidateClinicalEvidenceUseCase(reasoning_service=get_reasoning_service())
    return DifferentialDiagnosisAIFacade(
        generate_use_case=generate_use_case,
        rank_use_case=rank_use_case,
        validate_use_case=validate_use_case,
        renderer=get_result_renderer(),
        generator=generator,
    )
