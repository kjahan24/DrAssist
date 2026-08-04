"""Unit tests for `AIGatewayFacade` — the public port other modules are
expected to call, exercised here exactly as another module would call it
(through `AIGatewayPort`), per
`docs/backend-architecture/12_testing_architecture.md`'s "Contract tests"
framing, using fakes for its three collaborators."""

import pytest

from app.modules.ai.application.dto import PromptVariables
from app.modules.ai.application.use_cases.generate_chat_completion import GenerateChatCompletion
from app.modules.ai.application.use_cases.generate_embedding import GenerateEmbedding
from app.modules.ai.domain.enums import AIMessageRole, AIProviderType
from app.modules.ai.domain.exceptions import PromptTemplateNotFoundError
from app.modules.ai.domain.value_objects import AIMessage, AIModel
from app.modules.ai.infrastructure.prompts.in_memory_repository import (
    InMemoryPromptTemplateRepository,
)
from app.modules.ai.infrastructure.prompts.registry import PromptRegistry
from app.modules.ai.public.dto import ChatCompletionRequest, EmbeddingRequest
from app.modules.ai.public.facade import AIGatewayFacade
from app.modules.ai.public.interfaces import AIGatewayPort
from tests.unit.modules.ai.application.fakes import FakeAIProviderPort, FakeEmbeddingProviderPort


def _facade(
    *,
    chat_provider: FakeAIProviderPort | None = None,
    embedding_provider: FakeEmbeddingProviderPort | None = None,
    prompt_registry: PromptRegistry | None = None,
) -> AIGatewayFacade:
    return AIGatewayFacade(
        chat_completion_use_case=GenerateChatCompletion(
            provider=chat_provider or FakeAIProviderPort()
        ),
        embedding_use_case=GenerateEmbedding(
            provider=embedding_provider or FakeEmbeddingProviderPort()
        ),
        prompt_renderer=prompt_registry
        or PromptRegistry(repository=InMemoryPromptTemplateRepository()),
    )


class TestAIGatewayFacade:
    def test_is_an_ai_gateway_port(self) -> None:
        assert isinstance(_facade(), AIGatewayPort)

    async def test_generate_chat_completion_delegates_to_the_use_case(self) -> None:
        facade = _facade()
        request = ChatCompletionRequest(
            messages=(AIMessage(role=AIMessageRole.USER, content="hi"),),
            model=AIModel(provider=AIProviderType.MOCK, name="mock-model"),
        )

        response = await facade.generate_chat_completion(request)

        assert response.message.content == "fake reply"

    async def test_generate_embedding_delegates_to_the_use_case(self) -> None:
        facade = _facade()
        request = EmbeddingRequest(
            input_texts=("hi",), model=AIModel(provider=AIProviderType.MOCK, name="mock-embedding")
        )

        response = await facade.generate_embedding(request)

        assert len(response.embeddings) == 1

    async def test_render_prompt_delegates_to_the_prompt_registry(self) -> None:
        from app.modules.ai.domain.value_objects import PromptTemplate

        repository = InMemoryPromptTemplateRepository()
        registry = PromptRegistry(repository=repository)
        await registry.register(
            PromptTemplate(name="greeting", version=1, template_string="Hello {{ name }}!")
        )
        facade = _facade(prompt_registry=registry)

        rendered = await facade.render_prompt("greeting", PromptVariables({"name": "Ada"}))

        assert rendered == "Hello Ada!"

    async def test_render_prompt_propagates_not_found(self) -> None:
        facade = _facade()
        with pytest.raises(PromptTemplateNotFoundError):
            await facade.render_prompt("never-registered", PromptVariables.empty())
