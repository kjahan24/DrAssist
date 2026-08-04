"""`DefaultPrescriptionGenerator` — the one concrete
`PrescriptionGeneratorPort` implementation this task ships: selects a
prompt template set, renders it, and calls AI Foundation's public
`AIGatewayPort.generate_chat_completion` — never a provider SDK directly.

**Streaming** (`stream_generate`): reuses `app.shared.infrastructure
.text_processing.word_chunking.chunk_text_by_word` — see that function's
own docstring, and `app.modules.icd10_ai.infrastructure.generation
.icd10_generator.DefaultICD10Generator`'s module docstring, for the full
reasoning on why this is a post-hoc chunking of one complete
`generate_chat_completion` call rather than true token-level streaming
(AI Foundation's public `AIGatewayPort` does not expose the latter).

Streaming does **not** go through
`GeneratePrescriptionSuggestionUseCase`'s parse/validate/safety-analysis/
audit pipeline, the same scope `app.modules.icd10_ai` documents for
itself.
"""

from collections.abc import AsyncIterator
from time import perf_counter
from uuid import uuid4

from app.modules.ai.infrastructure.prompts.registry import PromptRegistry
from app.modules.ai.public.dto import AIModel, ChatCompletionRequest
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.prescription_ai.application.ports import (
    CostEstimatorPort,
    PrescriptionGeneratorPort,
    PrescriptionPromptBuilderPort,
    PrescriptionTemplateSelectorPort,
)
from app.modules.prescription_ai.domain.enums import GenerationStatus
from app.modules.prescription_ai.domain.value_objects import (
    GenerationSession,
    PrescriptionContextInput,
    PrescriptionStreamChunk,
)
from app.modules.prescription_ai.infrastructure.prompts.template_registrar import (
    ensure_prescription_templates_registered,
)
from app.shared.infrastructure.text_processing.word_chunking import chunk_text_by_word


class DefaultPrescriptionGenerator(PrescriptionGeneratorPort):
    def __init__(
        self,
        *,
        ai_gateway: AIGatewayPort,
        prompt_registry: PromptRegistry,
        template_selector: PrescriptionTemplateSelectorPort,
        prompt_builder: PrescriptionPromptBuilderPort,
        cost_estimator: CostEstimatorPort,
        default_model: AIModel,
    ) -> None:
        self._ai_gateway = ai_gateway
        self._prompt_registry = prompt_registry
        self._template_selector = template_selector
        self._prompt_builder = prompt_builder
        self._cost_estimator = cost_estimator
        self._default_model = default_model

    async def generate(self, context: PrescriptionContextInput) -> tuple[str, GenerationSession]:
        await ensure_prescription_templates_registered(self._prompt_registry)
        template_set = self._template_selector.select(context.prescribing_setting)
        messages = await self._prompt_builder.build_messages(context, template_set)

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
            prescribing_setting=context.prescribing_setting.value,
            language=context.language,
            status=GenerationStatus.COMPLETED,
            latency_ms=latency_ms,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            estimated_cost_usd=estimated_cost_usd,
        )
        return response.message.content, session

    async def stream_generate(
        self, context: PrescriptionContextInput
    ) -> AsyncIterator[PrescriptionStreamChunk]:
        raw_text, _session = await self.generate(context)
        for delta, is_final in chunk_text_by_word(raw_text):
            yield PrescriptionStreamChunk(delta=delta, is_final=is_final)
