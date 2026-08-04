"""AI module domain entity: `AIConversation`.

Extends `Entity`, not `AggregateRoot` — a conversation raises no domain
events and this task builds no persistence for it (no `ai_conversations`
table; see `container.py`'s scope note), so the event-collection machinery
`AggregateRoot` adds would sit unused. It still needs identity (two
conversations with the same messages are not "the same conversation"),
which is exactly what `Entity` provides on its own
(`app/shared/domain/entity.py`).

This is an in-process accumulator for building up a multi-turn message
list before handing it to `AIProviderPort.complete()` via
`ChatCompletionRequest.messages` — not a session/audit record (that's
`AiSession` in the future full AI Gateway module,
`09_ai_gateway_and_storage.md`).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.modules.ai.domain.enums import AIMessageRole
from app.modules.ai.domain.value_objects import AIMessage, AIModel
from app.shared.domain.entity import Entity


@dataclass(kw_only=True, eq=False)
class AIConversation(Entity):
    model: AIModel | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    _messages: list[AIMessage] = field(default_factory=list, repr=False)

    @property
    def messages(self) -> tuple[AIMessage, ...]:
        """Read-only view — per this codebase's own "entities are never
        mutated from outside their own methods" rule
        (`11_standards_and_conventions.md`), a caller adds a message via
        `add_message()`, never `conversation.messages.append(...)`."""
        return tuple(self._messages)

    def add_message(self, role: AIMessageRole, content: str, *, name: str | None = None) -> None:
        self._messages.append(AIMessage(role=role, content=content, name=name))

    def add_system_message(self, content: str) -> None:
        self.add_message(AIMessageRole.SYSTEM, content)

    def add_user_message(self, content: str) -> None:
        self.add_message(AIMessageRole.USER, content)

    def add_assistant_message(self, content: str) -> None:
        self.add_message(AIMessageRole.ASSISTANT, content)
