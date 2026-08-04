"""Module composition root for AI Clinical Note Generation.

Scope note — this task builds a **generation-only** module: it produces a
structured `ClinicalNote` from explicit encounter input and never
persists anything (no `clinical_note_ai_*` table, no repository, no
`domain/repositories.py`) — "It DOES NOT save notes. It ONLY generates AI
output." The eventual, persisted "Clinical Note" feature is a separate
future module expected to call this one's `public/interfaces.py
::ClinicalNoteAIPort` for AI-assisted drafts, the same relationship
`app.modules.ai_copilot` has to *its* own future clinical-feature
consumers.

Unlike `app.modules.ai_copilot`'s `container.py` (session-scoped — its
`ContextBuilder` reads seven peer modules' request-scoped facades), this
module owns no database session or per-request state at all: every input
field is supplied directly by the caller, so — like AI Foundation's own
`container.py` — every component built here is process-lifetime and
exposed as an `lru_cache`d singleton.

Depends on AI Foundation (`app.modules.ai`) directly, not through
`app.modules.ai_copilot` — this module's input is already fully self-
contained encounter data, not something needing `ai_copilot`'s patient-
history `ContextBuilder`; see `domain/value_objects.py`'s own module
docstring. `get_prompt_registry` is imported from AI Foundation's
`container.py` (not `.public/`, which does not expose it) specifically to
register this module's own prompt templates — the exact extension point
that module's own `get_prompt_registry` docstring names ("a future
clinical module registers its own templates... at its own `container.py`
import time"); nothing in AI Foundation's source is modified.
"""

from functools import lru_cache

from app.core.config import get_settings
from app.modules.ai.container import get_ai_gateway_facade, get_prompt_registry
from app.modules.clinical_note_ai.application.ports import (
    ClinicalNoteAuditLoggerPort,
    ClinicalNoteGeneratorPort,
    ClinicalNoteParserPort,
    ClinicalNoteValidatorPort,
    CostEstimatorPort,
    PromptBuilderPort,
    TemplateSelectorPort,
)
from app.modules.clinical_note_ai.application.services.clinical_note_renderer import (
    ClinicalNoteRenderer,
)
from app.modules.clinical_note_ai.application.use_cases.generate_clinical_note import (
    GenerateClinicalNoteUseCase,
)
from app.modules.clinical_note_ai.application.use_cases.render_clinical_note import (
    RenderClinicalNoteUseCase,
)
from app.modules.clinical_note_ai.application.use_cases.validate_clinical_input import (
    ValidateClinicalInputUseCase,
)
from app.modules.clinical_note_ai.infrastructure.audit.audit_logger import (
    StructlogClinicalNoteAuditLogger,
)
from app.modules.clinical_note_ai.infrastructure.cost.cost_estimator import CostEstimator
from app.modules.clinical_note_ai.infrastructure.generation.clinical_note_generator import (
    DefaultClinicalNoteGenerator,
)
from app.modules.clinical_note_ai.infrastructure.parsing.clinical_note_parser import (
    DefaultClinicalNoteParser,
)
from app.modules.clinical_note_ai.infrastructure.prompts.prompt_builder import DefaultPromptBuilder
from app.modules.clinical_note_ai.infrastructure.prompts.template_selector import (
    DefaultTemplateSelector,
)
from app.modules.clinical_note_ai.infrastructure.provider_selection import resolve_default_ai_model
from app.modules.clinical_note_ai.infrastructure.validation.clinical_note_validator import (
    DefaultClinicalNoteValidator,
)
from app.modules.clinical_note_ai.public.facade import ClinicalNoteAIFacade


@lru_cache
def get_output_parser() -> ClinicalNoteParserPort:
    return DefaultClinicalNoteParser()


@lru_cache
def get_note_validator() -> ClinicalNoteValidatorPort:
    return DefaultClinicalNoteValidator()


@lru_cache
def get_clinical_note_audit_logger() -> ClinicalNoteAuditLoggerPort:
    return StructlogClinicalNoteAuditLogger()


@lru_cache
def get_cost_estimator() -> CostEstimatorPort:
    return CostEstimator()


@lru_cache
def get_template_selector() -> TemplateSelectorPort:
    return DefaultTemplateSelector()


@lru_cache
def get_prompt_builder() -> PromptBuilderPort:
    return DefaultPromptBuilder(ai_gateway=get_ai_gateway_facade())


@lru_cache
def get_note_renderer() -> ClinicalNoteRenderer:
    return ClinicalNoteRenderer()


@lru_cache
def get_clinical_note_generator() -> ClinicalNoteGeneratorPort:
    settings = get_settings()
    return DefaultClinicalNoteGenerator(
        ai_gateway=get_ai_gateway_facade(),
        prompt_registry=get_prompt_registry(),
        template_selector=get_template_selector(),
        prompt_builder=get_prompt_builder(),
        cost_estimator=get_cost_estimator(),
        default_model=resolve_default_ai_model(settings),
    )


@lru_cache
def get_clinical_note_ai_facade() -> ClinicalNoteAIFacade:
    generator = get_clinical_note_generator()
    generate_use_case = GenerateClinicalNoteUseCase(
        generator=generator,
        parser=get_output_parser(),
        validator=get_note_validator(),
        audit_logger=get_clinical_note_audit_logger(),
    )
    validate_use_case = ValidateClinicalInputUseCase()
    render_use_case = RenderClinicalNoteUseCase(renderer=get_note_renderer())
    return ClinicalNoteAIFacade(
        generate_use_case=generate_use_case,
        validate_use_case=validate_use_case,
        render_use_case=render_use_case,
        generator=generator,
    )
