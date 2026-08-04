"""Module composition root for AI SOAP Note Generation.

Scope note — this task builds a **generation-only** module: it produces a
structured `SOAPNote` from explicit encounter input and never persists
anything (no `soap_note_ai_*` table, no repository) — "It ONLY generates
AI output. It DOES NOT save notes." The pre-existing `app.modules
.soap_notes` module (structured, persisted SOAP data — a completed
backend module, not modified by this task) is the expected future
consumer of this one's `public/interfaces.py::SOAPNoteAIPort` for AI-
assisted drafting; this module owns no overlap with its tables.

Not built on top of `app.modules.clinical_note_ai.public.interfaces
.ClinicalNoteAIPort` — SOAP notes (Subjective/Objective/Assessment/Plan,
four sections) and clinical notes (Chief Complaint/HPI/ROS/Physical Exam/
Assessment/Plan, six sections) are genuinely different structures, not
one a subset of the other, so there is no shape to reuse at the
generation-pipeline level. What *is* reused, per this task's own "REUSE"
section: (1) AI Foundation directly (`AIGatewayPort`, `PromptRegistry` —
exactly as `app.modules.clinical_note_ai.container` already does), and
(2) the genuinely module-agnostic mechanics extracted to
`app.shared.infrastructure.text_processing` (JSON extraction, placeholder
detection, word-chunked streaming) — see that package's own module
docstrings for why provider selection, cost estimation, and template
registration could *not* also move there (they need AI Foundation's own
types, and `app/shared/` may never import from `app/modules/`) and
therefore remain this module's own small, locally-owned copies, the same
"each module defines its own copy" precedent already established twice
elsewhere in this codebase.

Owns no database session or per-request state (see the above — no
persistence at all), so every component here is process-lifetime and
exposed as an `lru_cache`d singleton, the same shape
`app.modules.clinical_note_ai.container` uses for itself.
"""

from functools import lru_cache

from app.core.config import get_settings
from app.modules.ai.container import get_ai_gateway_facade, get_prompt_registry
from app.modules.soap_note_ai.application.ports import (
    CostEstimatorPort,
    SOAPGeneratorPort,
    SOAPNoteAuditLoggerPort,
    SOAPNoteParserPort,
    SOAPNoteValidatorPort,
    SOAPPromptBuilderPort,
    SOAPTemplateSelectorPort,
)
from app.modules.soap_note_ai.application.services.soap_note_renderer import SOAPNoteRenderer
from app.modules.soap_note_ai.application.use_cases.generate_soap_note import (
    GenerateSOAPNoteUseCase,
)
from app.modules.soap_note_ai.application.use_cases.render_soap_note import RenderSOAPNoteUseCase
from app.modules.soap_note_ai.application.use_cases.validate_soap_input import (
    ValidateSOAPInputUseCase,
)
from app.modules.soap_note_ai.infrastructure.audit.audit_logger import StructlogSOAPAuditLogger
from app.modules.soap_note_ai.infrastructure.cost.cost_estimator import CostEstimator
from app.modules.soap_note_ai.infrastructure.generation.soap_note_generator import (
    DefaultSOAPGenerator,
)
from app.modules.soap_note_ai.infrastructure.parsing.soap_note_parser import DefaultSOAPNoteParser
from app.modules.soap_note_ai.infrastructure.prompts.prompt_builder import DefaultSOAPPromptBuilder
from app.modules.soap_note_ai.infrastructure.prompts.template_selector import (
    DefaultSOAPTemplateSelector,
)
from app.modules.soap_note_ai.infrastructure.provider_selection import resolve_default_ai_model
from app.modules.soap_note_ai.infrastructure.validation.soap_note_validator import (
    DefaultSOAPNoteValidator,
)
from app.modules.soap_note_ai.public.facade import SOAPNoteAIFacade


@lru_cache
def get_output_parser() -> SOAPNoteParserPort:
    return DefaultSOAPNoteParser()


@lru_cache
def get_note_validator() -> SOAPNoteValidatorPort:
    return DefaultSOAPNoteValidator()


@lru_cache
def get_soap_note_audit_logger() -> SOAPNoteAuditLoggerPort:
    return StructlogSOAPAuditLogger()


@lru_cache
def get_cost_estimator() -> CostEstimatorPort:
    return CostEstimator()


@lru_cache
def get_template_selector() -> SOAPTemplateSelectorPort:
    return DefaultSOAPTemplateSelector()


@lru_cache
def get_prompt_builder() -> SOAPPromptBuilderPort:
    return DefaultSOAPPromptBuilder(ai_gateway=get_ai_gateway_facade())


@lru_cache
def get_note_renderer() -> SOAPNoteRenderer:
    return SOAPNoteRenderer()


@lru_cache
def get_soap_note_generator() -> SOAPGeneratorPort:
    settings = get_settings()
    return DefaultSOAPGenerator(
        ai_gateway=get_ai_gateway_facade(),
        prompt_registry=get_prompt_registry(),
        template_selector=get_template_selector(),
        prompt_builder=get_prompt_builder(),
        cost_estimator=get_cost_estimator(),
        default_model=resolve_default_ai_model(settings),
    )


@lru_cache
def get_soap_note_ai_facade() -> SOAPNoteAIFacade:
    generator = get_soap_note_generator()
    generate_use_case = GenerateSOAPNoteUseCase(
        generator=generator,
        parser=get_output_parser(),
        validator=get_note_validator(),
        audit_logger=get_soap_note_audit_logger(),
    )
    validate_use_case = ValidateSOAPInputUseCase()
    render_use_case = RenderSOAPNoteUseCase(renderer=get_note_renderer())
    return SOAPNoteAIFacade(
        generate_use_case=generate_use_case,
        validate_use_case=validate_use_case,
        render_use_case=render_use_case,
        generator=generator,
    )
