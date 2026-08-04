"""In-memory test doubles for the AI ICD-10 Coding module's application-
layer ports, plus a fake AI Foundation `AIGatewayPort` for infrastructure-
level tests — per `docs/backend-architecture/12_testing_architecture.md`
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
from app.modules.icd10_ai.application.ports import (
    ICD10AuditLoggerPort,
    ICD10GeneratorPort,
    ICD10KnowledgePort,
    ICD10SuggestionParserPort,
    ICD10SuggestionValidatorPort,
)
from app.modules.icd10_ai.domain.enums import DiagnosisFlag, GenerationStatus, ICD10OutputFormat
from app.modules.icd10_ai.domain.value_objects import (
    GenerationSession,
    ICD10CodingInput,
    ICD10StreamChunk,
    ICD10Suggestion,
    ICD10SuggestionSet,
)


def make_generation_session(**overrides: object) -> GenerationSession:
    defaults: dict[str, object] = {
        "generation_id": uuid4(),
        "provider": "mock",
        "model": "mock-model",
        "coding_setting": "outpatient",
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


def make_suggestion(**overrides: object) -> ICD10Suggestion:
    defaults: dict[str, object] = {
        "icd10_code": "J06.9",
        "diagnosis_name": "Acute upper respiratory infection, unspecified",
        "confidence_score": 0.85,
        "clinical_reasoning": "Supported by sore throat and fever",
        "supporting_evidence": "sore throat, fever",
        "flag": DiagnosisFlag.PRIMARY,
    }
    defaults.update(overrides)
    return ICD10Suggestion(**defaults)  # type: ignore[arg-type]


def make_suggestion_set(**overrides: object) -> ICD10SuggestionSet:
    defaults: dict[str, object] = {
        "suggestions": (make_suggestion(),),
        "raw_text": '{"suggestions": [{"icd10_code": "J06.9"}]}',
        "output_format": ICD10OutputFormat.JSON,
    }
    defaults.update(overrides)
    return ICD10SuggestionSet(**defaults)  # type: ignore[arg-type]


class FakeICD10GeneratorPort(ICD10GeneratorPort):
    def __init__(
        self,
        *,
        raw_text: str = '{"suggestions": [{"icd10_code": "J06.9"}]}',
        session: GenerationSession | None = None,
        error: Exception | None = None,
        stream_chunks: list[ICD10StreamChunk] | None = None,
    ) -> None:
        self._raw_text = raw_text
        self._session = session or make_generation_session()
        self._error = error
        self._stream_chunks = stream_chunks or [ICD10StreamChunk(delta=raw_text, is_final=True)]
        self.received_inputs: list[ICD10CodingInput] = []

    async def generate(self, coding_input: ICD10CodingInput) -> tuple[str, GenerationSession]:
        self.received_inputs.append(coding_input)
        if self._error is not None:
            raise self._error
        return self._raw_text, self._session

    async def stream_generate(
        self, coding_input: ICD10CodingInput
    ) -> AsyncIterator[ICD10StreamChunk]:
        self.received_inputs.append(coding_input)
        for chunk in self._stream_chunks:
            yield chunk


class FakeICD10SuggestionParserPort(ICD10SuggestionParserPort):
    def __init__(
        self, *, result: ICD10SuggestionSet | None = None, error: Exception | None = None
    ) -> None:
        self._result = result or make_suggestion_set()
        self._error = error
        self.received: list[tuple[str, ICD10OutputFormat]] = []

    def parse(self, raw_text: str, *, output_format: ICD10OutputFormat) -> ICD10SuggestionSet:
        self.received.append((raw_text, output_format))
        if self._error is not None:
            raise self._error
        return self._result


class FakeICD10SuggestionValidatorPort(ICD10SuggestionValidatorPort):
    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error
        self.received: list[ICD10SuggestionSet] = []

    def validate(self, suggestion_set: ICD10SuggestionSet) -> None:
        self.received.append(suggestion_set)
        if self._error is not None:
            raise self._error


class FakeICD10AuditLoggerPort(ICD10AuditLoggerPort):
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


class FakeICD10KnowledgePort(ICD10KnowledgePort):
    def __init__(
        self,
        *,
        valid_format_codes: set[str] | None = None,
        canonical_names: dict[str, str] | None = None,
        always_valid_format: bool = True,
    ) -> None:
        self._valid_format_codes = valid_format_codes
        self._canonical_names = canonical_names or {}
        self._always_valid_format = always_valid_format
        self.format_checks: list[str] = []
        self.lookups: list[str] = []

    def is_valid_format(self, icd10_code: str) -> bool:
        self.format_checks.append(icd10_code)
        if self._valid_format_codes is not None:
            return icd10_code.strip().upper() in self._valid_format_codes
        return self._always_valid_format

    def lookup_canonical_name(self, icd10_code: str) -> str | None:
        self.lookups.append(icd10_code)
        return self._canonical_names.get(icd10_code.strip().upper())


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
