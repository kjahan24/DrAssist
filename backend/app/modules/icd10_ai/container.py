"""Module composition root for AI ICD-10 Coding.

Scope note — this task builds a **generation-only** module: it suggests
structured `ICD10Suggestion`s from explicit clinical context and never
persists anything (no `icd10_ai_*` table, no repository) — "It ONLY
generates coding suggestions. It NEVER stores diagnoses. It NEVER
modifies patient records." The pre-existing `app.modules.icd10_coding`
module (structured, persisted coding records — a completed backend
module, not modified by this task) is the expected future consumer of
this one's `public/interfaces.py::ICD10AIPort` for AI-assisted coding;
this module owns no overlap with its tables. Prompt template names are
deliberately prefixed `icd10_suggestion`, not `icd10_coding`, to avoid
any reader confusing an AI-Foundation `PromptRegistry` string key with
that unrelated sibling module — see `infrastructure/prompts/templates.py`'s
own docstring.

REUSE, per this task's own section — "AI Foundation, AI Clinical Copilot,
AI Clinical Note AI, AI SOAP Note AI, Shared prompt framework, Shared
parser framework, Shared validation framework, Shared streaming
infrastructure": the module-independence rule ("modules may only import
each other's `public/` package") does not relax because a task's REUSE
wording is broader than a prior phase's — it is satisfied here exactly
as it was for `app.modules.soap_note_ai` (see that module's own
`container.py` scope note for the identical reasoning applied to its own
REUSE section): (1) AI Foundation directly (`AIGatewayPort`,
`PromptRegistry`), and (2) the genuinely module-agnostic mechanics in
`app.shared.infrastructure.text_processing` (JSON extraction, placeholder
detection, word-chunked streaming). Inspecting `ai_copilot`'s,
`clinical_note_ai`'s, and `soap_note_ai`'s own `public/` surfaces
confirms none of them expose anything ICD-10-coding-relevant to import
(their public contracts are about copilot orchestration, clinical notes,
and SOAP notes respectively, not shared parsing/validation utilities) —
so, as with `soap_note_ai`, the only remaining form of "reuse" available
is following the identical architectural PATTERN those modules already
established (template registrar idiom, cost estimator shape, provider
selection shape, audit logger shape), not importing their internals.
Provider selection, cost estimation, and template registration remain
this module's own small, locally-owned copies for the same reason
`app.shared.infrastructure.text_processing`'s own module docstrings
give: they need AI Foundation's own types, and `app/shared/` may never
import from `app/modules/`.

This module's input is fully self-contained clinical context (chief
complaint, HPI, symptoms, ROS, exam, assessment, plan, clinical/SOAP
note text, existing diagnoses), not an `app.modules.ai_copilot`-style
patient-history lookup — the same "explicit encounter input only" design
`app.modules.clinical_note_ai`/`app.modules.soap_note_ai` both use for
themselves.

Owns no database session or per-request state (see the above — no
persistence at all), so every component here is process-lifetime and
exposed as an `lru_cache`d singleton, the same shape
`app.modules.soap_note_ai.container` uses for itself.
"""

from functools import lru_cache

from app.core.config import get_settings
from app.modules.ai.container import get_ai_gateway_facade, get_prompt_registry
from app.modules.icd10_ai.application.ports import (
    CostEstimatorPort,
    ICD10AuditLoggerPort,
    ICD10GeneratorPort,
    ICD10KnowledgePort,
    ICD10PromptBuilderPort,
    ICD10SuggestionParserPort,
    ICD10SuggestionValidatorPort,
    ICD10TemplateSelectorPort,
)
from app.modules.icd10_ai.application.services.icd10_ranking_service import ICD10RankingService
from app.modules.icd10_ai.application.services.icd10_suggestion_renderer import (
    ICD10SuggestionRenderer,
)
from app.modules.icd10_ai.application.use_cases.generate_icd10_suggestions import (
    GenerateICD10SuggestionsUseCase,
)
from app.modules.icd10_ai.application.use_cases.rank_icd10_suggestions import (
    RankICD10SuggestionsUseCase,
)
from app.modules.icd10_ai.application.use_cases.validate_clinical_context import (
    ValidateClinicalContextUseCase,
)
from app.modules.icd10_ai.infrastructure.audit.audit_logger import StructlogICD10AuditLogger
from app.modules.icd10_ai.infrastructure.cost.cost_estimator import CostEstimator
from app.modules.icd10_ai.infrastructure.generation.icd10_generator import DefaultICD10Generator
from app.modules.icd10_ai.infrastructure.knowledge.icd10_knowledge_base import (
    StaticICD10KnowledgeBase,
)
from app.modules.icd10_ai.infrastructure.parsing.icd10_suggestion_parser import (
    DefaultICD10SuggestionParser,
)
from app.modules.icd10_ai.infrastructure.prompts.prompt_builder import DefaultICD10PromptBuilder
from app.modules.icd10_ai.infrastructure.prompts.template_selector import (
    DefaultICD10TemplateSelector,
)
from app.modules.icd10_ai.infrastructure.provider_selection import resolve_default_ai_model
from app.modules.icd10_ai.infrastructure.validation.icd10_suggestion_validator import (
    DefaultICD10SuggestionValidator,
)
from app.modules.icd10_ai.public.facade import ICD10AIFacade


@lru_cache
def get_output_parser() -> ICD10SuggestionParserPort:
    return DefaultICD10SuggestionParser()


@lru_cache
def get_knowledge_base() -> ICD10KnowledgePort:
    return StaticICD10KnowledgeBase()


@lru_cache
def get_suggestion_validator() -> ICD10SuggestionValidatorPort:
    return DefaultICD10SuggestionValidator(knowledge=get_knowledge_base())


@lru_cache
def get_icd10_audit_logger() -> ICD10AuditLoggerPort:
    return StructlogICD10AuditLogger()


@lru_cache
def get_cost_estimator() -> CostEstimatorPort:
    return CostEstimator()


@lru_cache
def get_template_selector() -> ICD10TemplateSelectorPort:
    return DefaultICD10TemplateSelector()


@lru_cache
def get_prompt_builder() -> ICD10PromptBuilderPort:
    return DefaultICD10PromptBuilder(ai_gateway=get_ai_gateway_facade())


@lru_cache
def get_ranking_service() -> ICD10RankingService:
    return ICD10RankingService(knowledge=get_knowledge_base())


@lru_cache
def get_suggestion_renderer() -> ICD10SuggestionRenderer:
    return ICD10SuggestionRenderer()


@lru_cache
def get_icd10_generator() -> ICD10GeneratorPort:
    settings = get_settings()
    return DefaultICD10Generator(
        ai_gateway=get_ai_gateway_facade(),
        prompt_registry=get_prompt_registry(),
        template_selector=get_template_selector(),
        prompt_builder=get_prompt_builder(),
        cost_estimator=get_cost_estimator(),
        default_model=resolve_default_ai_model(settings),
    )


@lru_cache
def get_icd10_ai_facade() -> ICD10AIFacade:
    generator = get_icd10_generator()
    generate_use_case = GenerateICD10SuggestionsUseCase(
        generator=generator,
        parser=get_output_parser(),
        validator=get_suggestion_validator(),
        ranking_service=get_ranking_service(),
        audit_logger=get_icd10_audit_logger(),
    )
    validate_use_case = ValidateClinicalContextUseCase()
    rank_use_case = RankICD10SuggestionsUseCase(ranking_service=get_ranking_service())
    return ICD10AIFacade(
        generate_use_case=generate_use_case,
        validate_use_case=validate_use_case,
        rank_use_case=rank_use_case,
        renderer=get_suggestion_renderer(),
        generator=generator,
    )
