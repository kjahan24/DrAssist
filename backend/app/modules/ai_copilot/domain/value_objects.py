"""Value objects for the AI Clinical Copilot module's domain.

Neither `AIRequest` nor `AISession` references any type from another
module's `domain`/`application`/`infrastructure` — cross-module data
(patient/visit identity, the AI provider/model actually used) is carried
here only as plain `UUID`/`str`/`int`/`float` primitives, never as a peer
module's own domain or `public` type, per this codebase's "domain code
never imports across module boundaries" rule (see
`app.modules.family_access.domain.value_objects`'s own docstring for the
precedent this follows).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from app.modules.ai_copilot.domain.enums import CopilotOutputFormat
from app.modules.ai_copilot.domain.exceptions import InvalidAIRequestError
from app.shared.domain.value_object import ValueObject


@dataclass(frozen=True, slots=True)
class AIRequest(ValueObject):
    """The caller's intent: "run AI orchestration `request_type` for
    `patient_id`, using prompt templates pinned at `prompt_version`."

    `prompt_version` is **required**, not optional — this task's own
    "Versioned templates only" requirement is read literally here: a
    caller must pin an exact version rather than implicitly asking for
    "latest", which also means `AISession.prompt_version` (recorded from
    this same field) is always the version that was actually used, with
    no ambiguity introduced by AI Foundation's `AIGatewayPort.render_prompt`
    not reporting back which version "latest" resolved to.

    `request_type` is a free-form, non-blank string rather than a closed
    enum deliberately — this module orchestrates AI requests for future
    clinical-feature modules (SOAP AI, ICD AI, ...) that don't exist yet;
    a closed enum here would need editing (violating "all changes must be
    additive") every time a new feature module is added. Each concrete
    `request_type` value is expected to have `"{request_type}.system"`/
    `".developer"`/`".user"` prompt templates registered in AI
    Foundation's `PromptRegistry` before it can actually be used — this
    module enforces no fixed vocabulary of valid values itself.
    """

    request_type: str
    patient_id: UUID
    prompt_version: int
    output_format: CopilotOutputFormat = CopilotOutputFormat.JSON
    visit_id: UUID | None = None
    model_override: str | None = None
    variables: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.request_type.strip():
            raise InvalidAIRequestError("request_type must not be blank")
        if self.prompt_version < 1:
            raise InvalidAIRequestError("prompt_version must be >= 1")


@dataclass(frozen=True, slots=True)
class AISession(ValueObject):
    """The tracked record of one completed AI Foundation call, per this
    task's own "AI Session" requirement (request id, provider, model,
    prompt version, latency, token usage, estimated cost).

    `provider`/`model` are plain `str`, not
    `app.modules.ai.public.dto.AIProviderType`/`AIModel` — this module's
    domain does not import even AI Foundation's *public* types (see this
    module's own docstring), so the provider/model actually used is
    recorded as the string AI Foundation's own response already carries
    (`ChatCompletionResponse.provider.value`/`.model.name`), read at the
    application layer where that public import *is* allowed
    (`application/services/clinical_copilot_service.py`).

    `estimated_cost_usd` comes from this module's own
    `infrastructure/cost/cost_estimator.py` — AI Foundation's
    `ChatCompletionResponse` carries no cost figure (cost estimation is
    internal to that module's `ResilientAIProvider` decorator, not part
    of its `public/` contract), so this module computes its own estimate
    independently from the token usage AI Foundation does return, the
    same "each module defines its own copy of a shape it needs" pattern
    `app.modules.documents.domain.value_objects.Sha256Checksum` and
    `app.modules.attachments.domain.value_objects.Sha256Checksum`
    establish twice already.
    """

    request_id: UUID
    provider: str
    model: str
    prompt_name: str
    prompt_version: int
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
