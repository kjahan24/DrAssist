"""The AI module's public port — the only contract another module may
depend on (`docs/backend-architecture/03_module_architecture.md`,
`10_module_communication.md`).

Never import from `app.modules.ai.domain`, `.application` (beyond this
package's own re-exports in `public/dto.py`), or `.infrastructure` from
outside this module. A future clinical module (Clinical Note, SOAP Note,
...) requesting AI assistance calls `AIGatewayPort.generate_chat_completion`
exactly as it would call `PatientQueryPort.get_patient_summary` today —
this port never knows what a "SOAP note" is, per this module's own
genericity (`03_module_architecture.md #10`).

This task builds no default-provider selection logic here on purpose —
`generate_chat_completion`/`generate_embedding` operate on whichever
provider `public/facade.py` was constructed with (`container.py` chooses
that from `AISettings.default_provider`); a caller needing a *specific*
non-default provider is out of scope until a real clinical feature
motivates that need (`container.py`'s own scope note).
"""

from abc import ABC, abstractmethod

from app.modules.ai.public.dto import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    PromptVariables,
)


class AIGatewayPort(ABC):
    @abstractmethod
    async def generate_chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse: ...

    @abstractmethod
    async def generate_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse: ...

    @abstractmethod
    async def render_prompt(
        self, name: str, variables: PromptVariables, *, version: int | None = None
    ) -> str: ...
