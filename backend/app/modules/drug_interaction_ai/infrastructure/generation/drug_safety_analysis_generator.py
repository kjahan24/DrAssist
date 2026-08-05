"""`DefaultDrugSafetyAnalysisGenerator` — the one concrete
`DrugSafetyAnalysisGeneratorPort` implementation this task ships: selects
a prompt template set, renders it, and calls AI Foundation's public
`AIGatewayPort.generate_chat_completion` — never a provider SDK directly.

**Streaming** (`stream_generate`): reuses `app.shared.infrastructure
.text_processing.word_chunking.chunk_text_by_word` — this task's own
"Reuse AI Foundation streaming" requirement. This is a post-hoc chunking
of one complete `generate_chat_completion` call rather than true
token-level streaming (AI Foundation's public `AIGatewayPort` does not
expose the latter), the same reasoning every prior AI module's own
generator documents for itself.

Streaming does **not** go through `AnalyzeMedicationSafetyUseCase`'s
parse/validate/enrichment/audit pipeline, the same scope every prior AI
module documents for itself.
"""

from collections.abc import AsyncIterator
from time import perf_counter
from uuid import uuid4

from app.modules.ai.infrastructure.prompts.registry import PromptRegistry
from app.modules.ai.public.dto import AIModel, ChatCompletionRequest
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.drug_interaction_ai.application.ports import (
    CostEstimatorPort,
    DrugSafetyAnalysisGeneratorPort,
    DrugSafetyAnalysisPromptBuilderPort,
    DrugSafetyAnalysisTemplateSelectorPort,
)
from app.modules.drug_interaction_ai.domain.enums import SafetyAnalysisStatus
from app.modules.drug_interaction_ai.domain.value_objects import (
    DrugInteractionAnalysisInput,
    DrugInteractionStreamChunk,
    GenerationSession,
)
from app.modules.drug_interaction_ai.infrastructure.prompts.template_registrar import (
    ensure_drug_interaction_templates_registered,
)
from app.shared.infrastructure.text_processing.word_chunking import chunk_text_by_word


class DefaultDrugSafetyAnalysisGenerator(DrugSafetyAnalysisGeneratorPort):
    def __init__(
        self,
        *,
        ai_gateway: AIGatewayPort,
        prompt_registry: PromptRegistry,
        template_selector: DrugSafetyAnalysisTemplateSelectorPort,
        prompt_builder: DrugSafetyAnalysisPromptBuilderPort,
        cost_estimator: CostEstimatorPort,
        default_model: AIModel,
    ) -> None:
        self._ai_gateway = ai_gateway
        self._prompt_registry = prompt_registry
        self._template_selector = template_selector
        self._prompt_builder = prompt_builder
        self._cost_estimator = cost_estimator
        self._default_model = default_model

    async def generate(
        self, input_dto: DrugInteractionAnalysisInput
    ) -> tuple[str, GenerationSession]:
        await ensure_drug_interaction_templates_registered(self._prompt_registry)
        template_set = self._template_selector.select(input_dto.medication_setting)
        messages = await self._prompt_builder.build_messages(input_dto, template_set)

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
            medication_setting=input_dto.medication_setting.value,
            language=input_dto.language,
            status=SafetyAnalysisStatus.COMPLETED,
            latency_ms=latency_ms,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            estimated_cost_usd=estimated_cost_usd,
        )
        return response.message.content, session

    async def stream_generate(
        self, input_dto: DrugInteractionAnalysisInput
    ) -> AsyncIterator[DrugInteractionStreamChunk]:
        raw_text, _session = await self.generate(input_dto)
        for delta, is_final in chunk_text_by_word(raw_text):
            yield DrugInteractionStreamChunk(delta=delta, is_final=is_final)
