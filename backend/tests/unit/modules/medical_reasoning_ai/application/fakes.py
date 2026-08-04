"""In-memory test doubles for the AI Medical Reasoning Engine's
application-layer ports, plus a fake AI Foundation `AIGatewayPort` for
infrastructure-level tests — per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default").
"""

from collections.abc import AsyncIterator
from dataclasses import replace
from uuid import UUID, uuid4

from app.modules.ai.public.dto import (
    AIFinishReason,
    AIMessage,
    AIMessageRole,
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    PromptVariables,
    TokenUsage,
)
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.medical_reasoning_ai.application.ports import (
    ConfidenceCalculatorPort,
    EvidenceAnalyzerPort,
    MedicalReasoningAuditLoggerPort,
    MedicalReasoningParserPort,
    MedicalReasoningPort,
    MedicalReasoningValidatorPort,
)
from app.modules.medical_reasoning_ai.domain.enums import (
    EvidencePolarity,
    MedicalReasoningOutputFormat,
    ReasoningStatus,
)
from app.modules.medical_reasoning_ai.domain.value_objects import (
    EvidenceItem,
    GenerationSession,
    MedicalReasoningInput,
    MedicalReasoningResult,
    MedicalReasoningStreamChunk,
    RedFlag,
)


def make_generation_session(**overrides: object) -> GenerationSession:
    defaults: dict[str, object] = {
        "generation_id": uuid4(),
        "provider": "mock",
        "model": "mock-model",
        "reasoning_setting": "outpatient",
        "language": "en",
        "status": ReasoningStatus.COMPLETED,
        "latency_ms": 1.0,
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
        "estimated_cost_usd": 0.0001,
    }
    defaults.update(overrides)
    return GenerationSession(**defaults)  # type: ignore[arg-type]


def make_evidence_item(**overrides: object) -> EvidenceItem:
    defaults: dict[str, object] = {
        "description": "Elevated troponin",
        "weight": 0.7,
        "polarity": EvidencePolarity.SUPPORTING,
    }
    defaults.update(overrides)
    return EvidenceItem(**defaults)  # type: ignore[arg-type]


def make_result(**overrides: object) -> MedicalReasoningResult:
    defaults: dict[str, object] = {
        "clinical_summary": "Patient presents with chest pain.",
        "evidence": (make_evidence_item(),),
        "missing_information": (),
        "clinical_confidence": 0.7,
        "diagnostic_confidence": 0.6,
        "therapeutic_confidence": 0.5,
        "risk_factors": (),
        "red_flags": (),
        "suggested_next_questions": (),
        "suggested_investigations": (),
        "suggested_monitoring": (),
        "clinical_justification": "Grounded in the elevated troponin.",
        "raw_text": '{"clinical_summary": "Patient presents with chest pain."}',
        "output_format": MedicalReasoningOutputFormat.JSON,
    }
    defaults.update(overrides)
    return MedicalReasoningResult(**defaults)  # type: ignore[arg-type]


class FakeMedicalReasoningPort(MedicalReasoningPort):
    def __init__(
        self,
        *,
        raw_text: str = '{"clinical_summary": "Patient presents with chest pain."}',
        session: GenerationSession | None = None,
        error: Exception | None = None,
        stream_chunks: list[MedicalReasoningStreamChunk] | None = None,
    ) -> None:
        self._raw_text = raw_text
        self._session = session or make_generation_session()
        self._error = error
        self._stream_chunks = stream_chunks or [
            MedicalReasoningStreamChunk(delta=raw_text, is_final=True)
        ]
        self.received_evidence: list[MedicalReasoningInput] = []

    async def generate(self, evidence: MedicalReasoningInput) -> tuple[str, GenerationSession]:
        self.received_evidence.append(evidence)
        if self._error is not None:
            raise self._error
        return self._raw_text, self._session

    async def stream_generate(
        self, evidence: MedicalReasoningInput
    ) -> AsyncIterator[MedicalReasoningStreamChunk]:
        self.received_evidence.append(evidence)
        for chunk in self._stream_chunks:
            yield chunk


class FakeMedicalReasoningParserPort(MedicalReasoningParserPort):
    def __init__(
        self, *, result: MedicalReasoningResult | None = None, error: Exception | None = None
    ) -> None:
        self._result = result or make_result()
        self._error = error
        self.received: list[tuple[str, MedicalReasoningOutputFormat]] = []

    def parse(
        self, raw_text: str, *, output_format: MedicalReasoningOutputFormat
    ) -> MedicalReasoningResult:
        self.received.append((raw_text, output_format))
        if self._error is not None:
            raise self._error
        return self._result


class FakeMedicalReasoningValidatorPort(MedicalReasoningValidatorPort):
    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error
        self.received: list[MedicalReasoningResult] = []

    def validate(self, result: MedicalReasoningResult) -> None:
        self.received.append(result)
        if self._error is not None:
            raise self._error


class FakeMedicalReasoningAuditLoggerPort(MedicalReasoningAuditLoggerPort):
    def __init__(self) -> None:
        self.sessions: list[GenerationSession] = []
        self.failures: list[dict[str, object]] = []

    async def log_generation(
        self, session: GenerationSession, *, organization_id: UUID, patient_id: UUID
    ) -> None:
        self.sessions.append(session)

    async def log_failure(
        self,
        *,
        generation_id: UUID,
        organization_id: UUID,
        patient_id: UUID,
        stage: str,
        error_code: str,
        message: str,
    ) -> None:
        self.failures.append(
            {
                "generation_id": generation_id,
                "organization_id": organization_id,
                "patient_id": patient_id,
                "stage": stage,
                "error_code": error_code,
                "message": message,
            }
        )


class FakeCostEstimator:
    def __init__(self, *, fixed_cost: float = 0.0042) -> None:
        self._fixed_cost = fixed_cost
        self.calls: list[dict[str, object]] = []

    def estimate(
        self, *, provider: str, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float:
        self.calls.append(
            {
                "provider": provider,
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            }
        )
        return self._fixed_cost


class FakeEvidenceAnalyzerPort(EvidenceAnalyzerPort):
    def __init__(
        self,
        *,
        weight_boost: float = 0.0,
        missing_information: tuple[str, ...] = (),
        risk_score: float = 0.0,
    ) -> None:
        self._weight_boost = weight_boost
        self._missing_information = missing_information
        self._risk_score = risk_score
        self.weighted_items: list[EvidenceItem] = []
        self.missing_information_calls: list[MedicalReasoningInput] = []
        self.risk_score_calls: list[dict[str, object]] = []

    def weight_evidence_item(self, item: EvidenceItem) -> EvidenceItem:
        self.weighted_items.append(item)
        if self._weight_boost == 0.0:
            return item
        return replace(item, weight=min(1.0, item.weight + self._weight_boost))

    def identify_missing_information(self, evidence: MedicalReasoningInput) -> tuple[str, ...]:
        self.missing_information_calls.append(evidence)
        return self._missing_information

    def compute_risk_score(
        self, *, risk_factors: tuple[str, ...], red_flags: tuple[RedFlag, ...]
    ) -> float:
        self.risk_score_calls.append({"risk_factors": risk_factors, "red_flags": red_flags})
        return self._risk_score


class FakeConfidenceCalculatorPort(ConfidenceCalculatorPort):
    def __init__(self, *, fallback_value: float = 0.42) -> None:
        self._fallback_value = fallback_value
        self.calls: list[dict[str, object]] = []

    def calculate_confidence(
        self,
        *,
        ai_reported: float | None,
        supporting_count: int,
        contradicting_count: int,
        missing_information_count: int,
    ) -> float:
        self.calls.append(
            {
                "ai_reported": ai_reported,
                "supporting_count": supporting_count,
                "contradicting_count": contradicting_count,
                "missing_information_count": missing_information_count,
            }
        )
        if ai_reported is not None:
            return ai_reported
        return self._fallback_value


class FakeAIGateway(AIGatewayPort):
    def __init__(
        self,
        *,
        chat_response: ChatCompletionResponse | None = None,
        rendered_prompts: dict[str, str] | None = None,
        chat_error: Exception | None = None,
    ) -> None:
        self._chat_response = chat_response
        self._rendered_prompts = rendered_prompts or {}
        self._chat_error = chat_error
        self.received_chat_requests: list[ChatCompletionRequest] = []
        self.rendered_calls: list[tuple[str, int | None]] = []

    async def generate_chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        self.received_chat_requests.append(request)
        if self._chat_error is not None:
            raise self._chat_error
        if self._chat_response is not None:
            return self._chat_response
        return ChatCompletionResponse(
            message=AIMessage(role=AIMessageRole.ASSISTANT, content='{"result": "ok"}'),
            model=request.model,
            provider=request.model.provider,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            finish_reason=AIFinishReason.STOP,
            latency_ms=1.0,
        )

    async def generate_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        return EmbeddingResponse(
            embeddings=tuple((0.0,) for _ in request.input_texts),
            model=request.model,
            provider=request.model.provider,
        )

    async def render_prompt(
        self, name: str, variables: PromptVariables, *, version: int | None = None
    ) -> str:
        self.rendered_calls.append((name, version))
        if name in self._rendered_prompts:
            return self._rendered_prompts[name]
        return f"rendered:{name}:v{version}"
