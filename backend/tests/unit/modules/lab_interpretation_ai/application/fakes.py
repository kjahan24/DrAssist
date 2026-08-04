"""In-memory test doubles for the AI Lab Interpretation module's
application-layer ports, plus a fake AI Foundation `AIGatewayPort` and a
fake peer-module `MedicalReasoningAIPort` for infrastructure/use-case-level
tests — per `docs/backend-architecture/12_testing_architecture.md`
("fakes over mocks as the default").
"""

from collections.abc import AsyncIterator
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
from app.modules.lab_interpretation_ai.application.ports import (
    CriticalValueAnalyzerPort,
    LabInterpretationAuditLoggerPort,
    LabInterpretationParserPort,
    LabInterpretationValidatorPort,
    LabInterpreterPort,
)
from app.modules.lab_interpretation_ai.domain.enums import (
    LabFindingFlag,
    LabInterpretationOutputFormat,
    LabInterpretationStatus,
)
from app.modules.lab_interpretation_ai.domain.value_objects import (
    GenerationSession,
    LabFinding,
    LabInterpretationInput,
    LabInterpretationResult,
    LabInterpretationStreamChunk,
    LabValue,
)
from app.modules.medical_reasoning_ai.public.dto import (
    EvidenceItem,
    GeneratedMedicalReasoning,
    MedicalReasoningInput,
    MedicalReasoningOutputFormat,
    MedicalReasoningResult,
    MedicalReasoningStreamChunk,
)
from app.modules.medical_reasoning_ai.public.interfaces import MedicalReasoningAIPort


def make_lab_value(**overrides: object) -> LabValue:
    defaults: dict[str, object] = {
        "test_name": "Potassium",
        "value": "4.2",
        "numeric_value": 4.2,
        "unit": "mmol/L",
        "reference_range": "3.5-5.0",
    }
    defaults.update(overrides)
    return LabValue(**defaults)  # type: ignore[arg-type]


def make_generation_session(**overrides: object) -> GenerationSession:
    defaults: dict[str, object] = {
        "generation_id": uuid4(),
        "provider": "mock",
        "model": "mock-model",
        "lab_setting": "outpatient",
        "language": "en",
        "status": LabInterpretationStatus.COMPLETED,
        "latency_ms": 1.0,
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
        "estimated_cost_usd": 0.0001,
    }
    defaults.update(overrides)
    return GenerationSession(**defaults)  # type: ignore[arg-type]


def make_finding(**overrides: object) -> LabFinding:
    defaults: dict[str, object] = {
        "test_name": "Potassium",
        "value": "4.2",
        "numeric_value": 4.2,
        "unit": "mmol/L",
        "flag": LabFindingFlag.NORMAL,
    }
    defaults.update(overrides)
    return LabFinding(**defaults)  # type: ignore[arg-type]


def make_result(**overrides: object) -> LabInterpretationResult:
    defaults: dict[str, object] = {
        "overall_interpretation": "Potassium is within normal limits.",
        "findings": (make_finding(),),
        "clinical_significance": "No acute electrolyte concern.",
        "supporting_evidence": (),
        "potential_causes": (),
        "suggested_follow_up_tests": (),
        "monitoring_recommendations": (),
        "red_flag_warnings": (),
        "confidence_score": 0.8,
        "raw_text": '{"overall_interpretation": "Potassium is within normal limits."}',
        "output_format": LabInterpretationOutputFormat.JSON,
    }
    defaults.update(overrides)
    return LabInterpretationResult(**defaults)  # type: ignore[arg-type]


class FakeLabInterpreterPort(LabInterpreterPort):
    def __init__(
        self,
        *,
        raw_text: str = '{"overall_interpretation": "Potassium is within normal limits."}',
        session: GenerationSession | None = None,
        error: Exception | None = None,
        stream_chunks: list[LabInterpretationStreamChunk] | None = None,
    ) -> None:
        self._raw_text = raw_text
        self._session = session or make_generation_session()
        self._error = error
        self._stream_chunks = stream_chunks or [
            LabInterpretationStreamChunk(delta=raw_text, is_final=True)
        ]
        self.received: list[LabInterpretationInput] = []

    async def generate(self, input_dto: LabInterpretationInput) -> tuple[str, GenerationSession]:
        self.received.append(input_dto)
        if self._error is not None:
            raise self._error
        return self._raw_text, self._session

    async def stream_generate(
        self, input_dto: LabInterpretationInput
    ) -> AsyncIterator[LabInterpretationStreamChunk]:
        self.received.append(input_dto)
        for chunk in self._stream_chunks:
            yield chunk


class FakeLabInterpretationParserPort(LabInterpretationParserPort):
    def __init__(
        self, *, result: LabInterpretationResult | None = None, error: Exception | None = None
    ) -> None:
        self._result = result or make_result()
        self._error = error
        self.received: list[tuple[str, LabInterpretationOutputFormat]] = []

    def parse(
        self, raw_text: str, *, output_format: LabInterpretationOutputFormat
    ) -> LabInterpretationResult:
        self.received.append((raw_text, output_format))
        if self._error is not None:
            raise self._error
        return self._result


class FakeLabInterpretationValidatorPort(LabInterpretationValidatorPort):
    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error
        self.received: list[LabInterpretationResult] = []

    def validate(self, result: LabInterpretationResult) -> None:
        self.received.append(result)
        if self._error is not None:
            raise self._error


class FakeLabInterpretationAuditLoggerPort(LabInterpretationAuditLoggerPort):
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


class FakeCriticalValueAnalyzerPort(CriticalValueAnalyzerPort):
    def __init__(self, *, classification: LabFindingFlag | None = None) -> None:
        self._classification = classification
        self.calls: list[dict[str, object]] = []

    def classify(self, *, test_name: str, numeric_value: float | None) -> LabFindingFlag | None:
        self.calls.append({"test_name": test_name, "numeric_value": numeric_value})
        return self._classification


class FakeMedicalReasoningAIPort(MedicalReasoningAIPort):
    def __init__(self, *, confidence_value: float = 0.55) -> None:
        self._confidence_value = confidence_value
        self.score_confidence_calls: list[dict[str, object]] = []

    async def generate_reasoning(
        self, evidence: MedicalReasoningInput
    ) -> GeneratedMedicalReasoning:
        raise NotImplementedError("not exercised by lab_interpretation_ai's own tests")

    def stream_generate_reasoning(
        self, evidence: MedicalReasoningInput
    ) -> AsyncIterator[MedicalReasoningStreamChunk]:
        raise NotImplementedError("not exercised by lab_interpretation_ai's own tests")

    async def render_result(
        self, result: MedicalReasoningResult, *, target_format: MedicalReasoningOutputFormat
    ) -> str:
        raise NotImplementedError("not exercised by lab_interpretation_ai's own tests")

    def weight_evidence(self, items: tuple[EvidenceItem, ...]) -> tuple[EvidenceItem, ...]:
        raise NotImplementedError("not exercised by lab_interpretation_ai's own tests")

    def score_confidence(
        self,
        *,
        ai_reported: float | None,
        supporting_count: int,
        contradicting_count: int,
        missing_information_count: int,
    ) -> float:
        self.score_confidence_calls.append(
            {
                "ai_reported": ai_reported,
                "supporting_count": supporting_count,
                "contradicting_count": contradicting_count,
                "missing_information_count": missing_information_count,
            }
        )
        if ai_reported is not None:
            return ai_reported
        return self._confidence_value


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
