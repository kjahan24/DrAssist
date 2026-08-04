"""In-memory test doubles for the AI Differential Diagnosis module's
application-layer ports, plus a fake AI Foundation `AIGatewayPort` for
infrastructure-level tests — per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default").
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
from app.modules.differential_diagnosis_ai.application.ports import (
    ClinicalReasoningPort,
    DifferentialDiagnosisAuditLoggerPort,
    DifferentialDiagnosisGeneratorPort,
    DifferentialDiagnosisParserPort,
    DifferentialDiagnosisValidatorPort,
)
from app.modules.differential_diagnosis_ai.domain.enums import (
    DifferentialOutputFormat,
    GenerationStatus,
    UrgencyLevel,
)
from app.modules.differential_diagnosis_ai.domain.value_objects import (
    DifferentialDiagnosisCandidate,
    DifferentialDiagnosisInput,
    DifferentialDiagnosisResult,
    DifferentialDiagnosisStreamChunk,
    GenerationSession,
)


def make_generation_session(**overrides: object) -> GenerationSession:
    defaults: dict[str, object] = {
        "generation_id": uuid4(),
        "provider": "mock",
        "model": "mock-model",
        "clinical_setting": "outpatient",
        "language": "en",
        "status": GenerationStatus.COMPLETED,
        "latency_ms": 1.0,
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
        "estimated_cost_usd": 0.0001,
    }
    defaults.update(overrides)
    return GenerationSession(**defaults)  # type: ignore[arg-type]


def make_candidate(**overrides: object) -> DifferentialDiagnosisCandidate:
    defaults: dict[str, object] = {
        "disease_name": "Pneumonia",
        "icd10_code": "J18.9",
        "confidence_score": 0.7,
        "clinical_reasoning": "Consistent with fever and productive cough",
        "supporting_findings": ("fever", "productive cough"),
        "findings_against": (),
        "recommended_next_tests": ("chest x-ray",),
        "red_flag_indicators": (),
        "urgency_level": UrgencyLevel.URGENT,
    }
    defaults.update(overrides)
    return DifferentialDiagnosisCandidate(**defaults)  # type: ignore[arg-type]


def make_result(**overrides: object) -> DifferentialDiagnosisResult:
    defaults: dict[str, object] = {
        "candidates": (make_candidate(),),
        "serious_diagnoses_not_to_miss": (),
        "suggested_investigations": (),
        "suggested_referrals": (),
        "raw_text": '{"candidates": [{"disease_name": "Pneumonia"}]}',
        "output_format": DifferentialOutputFormat.JSON,
    }
    defaults.update(overrides)
    return DifferentialDiagnosisResult(**defaults)  # type: ignore[arg-type]


class FakeDifferentialDiagnosisGeneratorPort(DifferentialDiagnosisGeneratorPort):
    def __init__(
        self,
        *,
        raw_text: str = '{"candidates": [{"disease_name": "Pneumonia"}]}',
        session: GenerationSession | None = None,
        error: Exception | None = None,
        stream_chunks: list[DifferentialDiagnosisStreamChunk] | None = None,
    ) -> None:
        self._raw_text = raw_text
        self._session = session or make_generation_session()
        self._error = error
        self._stream_chunks = stream_chunks or [
            DifferentialDiagnosisStreamChunk(delta=raw_text, is_final=True)
        ]
        self.received_evidence: list[DifferentialDiagnosisInput] = []

    async def generate(self, evidence: DifferentialDiagnosisInput) -> tuple[str, GenerationSession]:
        self.received_evidence.append(evidence)
        if self._error is not None:
            raise self._error
        return self._raw_text, self._session

    async def stream_generate(
        self, evidence: DifferentialDiagnosisInput
    ) -> AsyncIterator[DifferentialDiagnosisStreamChunk]:
        self.received_evidence.append(evidence)
        for chunk in self._stream_chunks:
            yield chunk


class FakeDifferentialDiagnosisParserPort(DifferentialDiagnosisParserPort):
    def __init__(
        self, *, result: DifferentialDiagnosisResult | None = None, error: Exception | None = None
    ) -> None:
        self._result = result or make_result()
        self._error = error
        self.received: list[tuple[str, DifferentialOutputFormat]] = []

    def parse(
        self, raw_text: str, *, output_format: DifferentialOutputFormat
    ) -> DifferentialDiagnosisResult:
        self.received.append((raw_text, output_format))
        if self._error is not None:
            raise self._error
        return self._result


class FakeDifferentialDiagnosisValidatorPort(DifferentialDiagnosisValidatorPort):
    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error
        self.received: list[DifferentialDiagnosisResult] = []

    def validate(self, result: DifferentialDiagnosisResult) -> None:
        self.received.append(result)
        if self._error is not None:
            raise self._error


class FakeDifferentialDiagnosisAuditLoggerPort(DifferentialDiagnosisAuditLoggerPort):
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


class FakeClinicalReasoningPort(ClinicalReasoningPort):
    def __init__(
        self,
        *,
        minimum_urgency: UrgencyLevel | None = None,
        missing_information: tuple[str, ...] = (),
    ) -> None:
        self._minimum_urgency = minimum_urgency
        self._missing_information = missing_information
        self.urgency_calls: list[dict[str, object]] = []
        self.missing_information_calls: list[DifferentialDiagnosisInput] = []

    def classify_minimum_urgency(
        self, *, red_flag_indicators: tuple[str, ...], confidence_score: float | None
    ) -> UrgencyLevel:
        self.urgency_calls.append(
            {"red_flag_indicators": red_flag_indicators, "confidence_score": confidence_score}
        )
        if self._minimum_urgency is not None:
            return self._minimum_urgency
        return UrgencyLevel.URGENT if red_flag_indicators else UrgencyLevel.ROUTINE

    def identify_missing_information(self, evidence: DifferentialDiagnosisInput) -> tuple[str, ...]:
        self.missing_information_calls.append(evidence)
        return self._missing_information


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
