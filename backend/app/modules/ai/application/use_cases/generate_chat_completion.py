"""`GenerateChatCompletion` — the Application-layer entry point a future
clinical module (Clinical Note, SOAP Note, ...) is expected to call
through this module's `public/facade.py`, rather than reaching into
`app.modules.ai.infrastructure` directly (`10_module_communication.md`'s
module-boundary rule).

Deliberately thin: the `AIProviderPort` this use case is constructed with
is expected to already be the fully-wrapped
`infrastructure/providers/resilient_provider.py::ResilientAIProvider`
(retry/timeout/audit/cost applied) that `container.py` builds — this use
case's only job is to be a stable, provider-agnostic seam other modules
depend on, not to re-implement resilience concerns
(`09_ai_gateway_and_storage.md`: "the Application layer's use cases call
the port and simply handle it succeeded or it raised").
"""

from app.modules.ai.application.dto import ChatCompletionRequest, ChatCompletionResponse
from app.modules.ai.application.ports import AIProviderPort
from app.shared.application.use_case import UseCase


class GenerateChatCompletion(UseCase[ChatCompletionRequest, ChatCompletionResponse]):
    def __init__(self, *, provider: AIProviderPort) -> None:
        self._provider = provider

    async def execute(self, input_dto: ChatCompletionRequest) -> ChatCompletionResponse:
        return await self._provider.complete(input_dto)
