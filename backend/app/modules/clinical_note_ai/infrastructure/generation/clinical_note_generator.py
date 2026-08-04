"""`DefaultClinicalNoteGenerator` — the one concrete
`ClinicalNoteGeneratorPort` implementation this task ships: selects a
prompt template set, renders it, and calls AI Foundation's public
`AIGatewayPort.generate_chat_completion` — never a provider SDK directly
(rule 4).

**Streaming** (`stream_generate`): AI Foundation's public `AIGatewayPort`
does not expose token-level streaming — only `generate_chat_completion`
(non-streaming) and `generate_embedding`/`render_prompt`. Real streaming
exists one layer down, on `AIProviderPort.stream_complete`
(`app.modules.ai.application.ports`), which is not part of that module's
`public/` surface; adding it there would be a genuine capability change
to a completed module, not the narrow "strictly required for dependency
injection" exception this task's own rules carve out for touching
completed modules (unlike the prompt-template registration in
`template_registrar.py`, which AI Foundation's own `container.py`
docstring explicitly anticipates). This method therefore satisfies
"support streaming responses" at *this* module's own boundary: it makes
one ordinary `generate_chat_completion` call and re-emits the resulting
text as word-level `ClinicalNoteStreamChunk`s, the same "simulate
streaming by chunking a complete response" approach AI Foundation's own
`infrastructure/llm/mock_provider.py::MockAIProvider.stream_complete`
already uses for the identical reason. A caller gets an incrementally-
consumable response shape today; true token-level streaming becomes a
drop-in change here alone if AI Foundation's public contract ever grows
to support it.

Streaming does **not** go through `GenerateClinicalNoteUseCase`'s parse/
validate/audit pipeline — it returns raw incremental text for progressive
display, not a validated `ClinicalNote`; a caller wanting the structured,
validated result still calls the non-streaming `generate` path (via
`GenerateClinicalNoteUseCase`).
"""

from collections.abc import AsyncIterator
from time import perf_counter
from uuid import uuid4

from app.modules.ai.infrastructure.prompts.registry import PromptRegistry
from app.modules.ai.public.dto import AIModel, ChatCompletionRequest
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.clinical_note_ai.application.ports import (
    ClinicalNoteGeneratorPort,
    CostEstimatorPort,
    PromptBuilderPort,
    TemplateSelectorPort,
)
from app.modules.clinical_note_ai.domain.enums import GenerationStatus
from app.modules.clinical_note_ai.domain.value_objects import (
    ClinicalEncounterInput,
    ClinicalNoteStreamChunk,
    GenerationSession,
)
from app.modules.clinical_note_ai.infrastructure.prompts.template_registrar import (
    ensure_clinical_note_templates_registered,
)


class DefaultClinicalNoteGenerator(ClinicalNoteGeneratorPort):
    def __init__(
        self,
        *,
        ai_gateway: AIGatewayPort,
        prompt_registry: PromptRegistry,
        template_selector: TemplateSelectorPort,
        prompt_builder: PromptBuilderPort,
        cost_estimator: CostEstimatorPort,
        default_model: AIModel,
    ) -> None:
        self._ai_gateway = ai_gateway
        self._prompt_registry = prompt_registry
        self._template_selector = template_selector
        self._prompt_builder = prompt_builder
        self._cost_estimator = cost_estimator
        self._default_model = default_model

    async def generate(self, encounter: ClinicalEncounterInput) -> tuple[str, GenerationSession]:
        await ensure_clinical_note_templates_registered(self._prompt_registry)
        template_set = self._template_selector.select(encounter.note_style)
        messages = await self._prompt_builder.build_messages(encounter, template_set)

        start = perf_counter()
        response = await self._ai_gateway.generate_chat_completion(
            ChatCompletionRequest(messages=tuple(messages), model=self._default_model)
        )
        latency_ms = (perf_counter() - start) * 1000

        estimated_cost_usd = self._cost_estimator.estimate(
            provider=response.provider.value,
            model=response.model.name,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )
        session = GenerationSession(
            generation_id=uuid4(),
            provider=response.provider.value,
            model=response.model.name,
            note_style=encounter.note_style.value,
            language=encounter.language,
            status=GenerationStatus.COMPLETED,
            latency_ms=latency_ms,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            estimated_cost_usd=estimated_cost_usd,
        )
        return response.message.content, session

    async def stream_generate(
        self, encounter: ClinicalEncounterInput
    ) -> AsyncIterator[ClinicalNoteStreamChunk]:
        raw_text, _session = await self.generate(encounter)
        words = raw_text.split(" ")
        for index, word in enumerate(words):
            is_final = index == len(words) - 1
            yield ClinicalNoteStreamChunk(
                delta=word if index == 0 else f" {word}", is_final=is_final
            )
