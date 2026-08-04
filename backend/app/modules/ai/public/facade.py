"""`AIGatewayFacade` — the one concrete implementation of `AIGatewayPort`.
Constructed by `app.modules.ai.container.build_ai_gateway_facade`, which
is the only place the two use cases and the concrete `PromptRegistry`
actually get wired together (see that module for why this task builds no
per-request/session construction here — the AI module is stateless
infrastructure, not a DB-backed aggregate).
"""

from app.modules.ai.application.ports import PromptRenderingPort
from app.modules.ai.application.use_cases.generate_chat_completion import GenerateChatCompletion
from app.modules.ai.application.use_cases.generate_embedding import GenerateEmbedding
from app.modules.ai.public.dto import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    PromptVariables,
)
from app.modules.ai.public.interfaces import AIGatewayPort


class AIGatewayFacade(AIGatewayPort):
    def __init__(
        self,
        *,
        chat_completion_use_case: GenerateChatCompletion,
        embedding_use_case: GenerateEmbedding,
        prompt_renderer: PromptRenderingPort,
    ) -> None:
        self._chat_completion_use_case = chat_completion_use_case
        self._embedding_use_case = embedding_use_case
        self._prompt_renderer = prompt_renderer

    async def generate_chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        return await self._chat_completion_use_case.execute(request)

    async def generate_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        return await self._embedding_use_case.execute(request)

    async def render_prompt(
        self, name: str, variables: PromptVariables, *, version: int | None = None
    ) -> str:
        return await self._prompt_renderer.render(name, variables, version=version)
