"""`GenerateEmbedding` — the embedding-side counterpart to
`GenerateChatCompletion`; see that module's docstring for why this stays
deliberately thin."""

from app.modules.ai.application.dto import EmbeddingRequest, EmbeddingResponse
from app.modules.ai.application.ports import EmbeddingProviderPort
from app.shared.application.use_case import UseCase


class GenerateEmbedding(UseCase[EmbeddingRequest, EmbeddingResponse]):
    def __init__(self, *, provider: EmbeddingProviderPort) -> None:
        self._provider = provider

    async def execute(self, input_dto: EmbeddingRequest) -> EmbeddingResponse:
        return await self._provider.embed(input_dto)
