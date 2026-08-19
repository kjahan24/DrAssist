"""`DefaultCommunityAIGenerator` — the one concrete implementation of
`CommunityAIGeneratorPort`. Calls only `AIGatewayPort.generate_chat_completion`
/`.render_prompt` — never a provider SDK, never
`app.modules.ai.infrastructure` — the identical "own module-local
generator, calls only the public gateway" shape every `*_ai` module's own
`infrastructure/generation/<name>_generator.py` already establishes (e.g.
`app.modules.medical_reasoning_ai.infrastructure.generation
.medical_reasoning_generator.DefaultMedicalReasoningGenerator`).

Parses each response via the shared kernel's `extract_json_object`
(`app.shared.infrastructure.text_processing.json_extraction`) — the same
"strip a markdown fence, `json.loads`, confirm it's an object" primitive
`ai_copilot`/`clinical_note_ai`/`soap_note_ai`/`icd10_ai` each already
reuse for this exact purpose — then converts the resulting dict into this
module's own typed value object via `application/services
._result_serialization.py`'s `*_from_dict` functions (reused for both
this write path and the read path that later deserializes a persisted
row back into a response DTO, so there is exactly one definition of each
shape's JSON contract).

`generate_resource_recommendations` additionally drops any recommendation
whose `source_url` does not exactly match a `catalog` entry — the
structural "Do NOT fabricate medical sources" enforcement `application
/ports.py`'s own docstring describes; the prompt instructs the model not
to invent one, but this filter is what actually guarantees it never
reaches a caller even if the model doesn't comply.
"""

from collections.abc import Sequence
from time import perf_counter

from app.modules.ai.infrastructure.prompts.registry import PromptRegistry
from app.modules.ai.public.dto import (
    AIMessage,
    AIMessageRole,
    AIModel,
    ChatCompletionRequest,
    ChatCompletionResponse,
    PromptVariables,
)
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.community_ai.application.dto import GenerationMetadata
from app.modules.community_ai.application.ports import CommunityAIGeneratorPort
from app.modules.community_ai.application.services._result_serialization import (
    misinformation_assessment_from_dict,
    resource_recommendations_from_dict,
    summary_from_dict,
)
from app.modules.community_ai.domain.exceptions import InvalidAnalysisResultError
from app.modules.community_ai.domain.value_objects import (
    CommunityDiscussionSummary,
    MisinformationAssessment,
    TrustedMedicalSource,
    TrustedResourceRecommendation,
)
from app.modules.community_ai.infrastructure.prompts.template_registrar import (
    ensure_community_ai_templates_registered,
)
from app.modules.community_ai.infrastructure.prompts.templates import (
    MISINFORMATION_SYSTEM_TEMPLATE_NAME,
    MISINFORMATION_TEMPLATE_VERSION,
    MISINFORMATION_USER_TEMPLATE_NAME,
    RESOURCE_RECOMMENDATION_SYSTEM_TEMPLATE_NAME,
    RESOURCE_RECOMMENDATION_TEMPLATE_VERSION,
    RESOURCE_RECOMMENDATION_USER_TEMPLATE_NAME,
    SUMMARY_SYSTEM_TEMPLATE_NAME,
    SUMMARY_TEMPLATE_VERSION,
    SUMMARY_USER_TEMPLATE_NAME,
)
from app.shared.infrastructure.text_processing.json_extraction import extract_json_object


def _parse_json(raw_text: str, *, context: str) -> dict[str, object]:
    try:
        return extract_json_object(raw_text)
    except ValueError as exc:
        raise InvalidAnalysisResultError(f"malformed {context} response: {exc}") from exc


class DefaultCommunityAIGenerator(CommunityAIGeneratorPort):
    def __init__(
        self, *, ai_gateway: AIGatewayPort, prompt_registry: PromptRegistry, default_model: AIModel
    ) -> None:
        self._ai_gateway = ai_gateway
        self._prompt_registry = prompt_registry
        self._default_model = default_model

    async def generate_summary(
        self, *, title: str | None, text: str
    ) -> tuple[CommunityDiscussionSummary, GenerationMetadata]:
        await ensure_community_ai_templates_registered(self._prompt_registry)
        system_text = await self._ai_gateway.render_prompt(
            SUMMARY_SYSTEM_TEMPLATE_NAME, PromptVariables.empty(), version=SUMMARY_TEMPLATE_VERSION
        )
        user_text = await self._ai_gateway.render_prompt(
            SUMMARY_USER_TEMPLATE_NAME,
            PromptVariables({"title": title or "Untitled", "text": text}),
            version=SUMMARY_TEMPLATE_VERSION,
        )
        response, latency_ms = await self._complete(system_text, user_text)
        payload = _parse_json(response.message.content, context="summary")
        try:
            summary = summary_from_dict(payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidAnalysisResultError(f"malformed summary response: {exc}") from exc
        return summary, GenerationMetadata(
            provider=response.provider.value, model=response.model.name, latency_ms=latency_ms
        )

    async def generate_misinformation_assessment(
        self, *, title: str | None, text: str
    ) -> tuple[MisinformationAssessment, GenerationMetadata]:
        await ensure_community_ai_templates_registered(self._prompt_registry)
        system_text = await self._ai_gateway.render_prompt(
            MISINFORMATION_SYSTEM_TEMPLATE_NAME,
            PromptVariables.empty(),
            version=MISINFORMATION_TEMPLATE_VERSION,
        )
        user_text = await self._ai_gateway.render_prompt(
            MISINFORMATION_USER_TEMPLATE_NAME,
            PromptVariables({"title": title or "Untitled", "text": text}),
            version=MISINFORMATION_TEMPLATE_VERSION,
        )
        response, latency_ms = await self._complete(system_text, user_text)
        payload = _parse_json(response.message.content, context="misinformation")
        try:
            assessment = misinformation_assessment_from_dict(payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidAnalysisResultError(f"malformed misinformation response: {exc}") from exc
        return assessment, GenerationMetadata(
            provider=response.provider.value, model=response.model.name, latency_ms=latency_ms
        )

    async def generate_resource_recommendations(
        self, *, title: str | None, text: str, catalog: Sequence[TrustedMedicalSource]
    ) -> tuple[tuple[TrustedResourceRecommendation, ...], GenerationMetadata]:
        await ensure_community_ai_templates_registered(self._prompt_registry)
        catalog_text = "\n".join(
            f"- {source.title} ({source.resource_type.value}): {source.url}" for source in catalog
        )
        system_text = await self._ai_gateway.render_prompt(
            RESOURCE_RECOMMENDATION_SYSTEM_TEMPLATE_NAME,
            PromptVariables.empty(),
            version=RESOURCE_RECOMMENDATION_TEMPLATE_VERSION,
        )
        user_text = await self._ai_gateway.render_prompt(
            RESOURCE_RECOMMENDATION_USER_TEMPLATE_NAME,
            PromptVariables({"title": title or "Untitled", "text": text, "catalog": catalog_text}),
            version=RESOURCE_RECOMMENDATION_TEMPLATE_VERSION,
        )
        response, latency_ms = await self._complete(system_text, user_text)
        payload = _parse_json(response.message.content, context="resource recommendation")
        try:
            recommendations = resource_recommendations_from_dict(payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidAnalysisResultError(
                f"malformed resource recommendation response: {exc}"
            ) from exc

        catalog_urls = {source.url for source in catalog}
        validated = tuple(r for r in recommendations if r.source_url in catalog_urls)
        return validated, GenerationMetadata(
            provider=response.provider.value, model=response.model.name, latency_ms=latency_ms
        )

    async def _complete(
        self, system_text: str, user_text: str
    ) -> tuple[ChatCompletionResponse, float]:
        messages = (
            AIMessage(role=AIMessageRole.SYSTEM, content=system_text),
            AIMessage(role=AIMessageRole.USER, content=user_text),
        )
        start = perf_counter()
        response = await self._ai_gateway.generate_chat_completion(
            ChatCompletionRequest(
                messages=messages, model=self._default_model, response_format="json"
            )
        )
        latency_ms = (perf_counter() - start) * 1000
        return response, latency_ms
