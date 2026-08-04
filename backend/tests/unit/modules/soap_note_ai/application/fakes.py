"""In-memory test doubles for the AI SOAP Note Generation module's
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
from app.modules.soap_note_ai.application.ports import (
    SOAPGeneratorPort,
    SOAPNoteAuditLoggerPort,
    SOAPNoteParserPort,
    SOAPNoteValidatorPort,
)
from app.modules.soap_note_ai.domain.enums import GenerationStatus, SOAPNoteOutputFormat
from app.modules.soap_note_ai.domain.value_objects import (
    GenerationSession,
    SOAPEncounterInput,
    SOAPNote,
    SOAPNoteStreamChunk,
    SOAPSection,
)


def make_generation_session(**overrides: object) -> GenerationSession:
    defaults: dict[str, object] = {
        "generation_id": uuid4(),
        "provider": "mock",
        "model": "mock-model",
        "soap_style": "standard",
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


def make_soap_note(**overrides: object) -> SOAPNote:
    defaults: dict[str, object] = {
        "sections": (
            SOAPSection(name="subjective", content="Reports headache since yesterday"),
            SOAPSection(name="objective", content="BP 120/80, afebrile"),
            SOAPSection(name="assessment", content="Tension headache"),
            SOAPSection(name="plan", content="OTC analgesics, follow up in 1 week"),
        ),
        "raw_text": '{"subjective": "Reports headache since yesterday"}',
        "output_format": SOAPNoteOutputFormat.JSON,
    }
    defaults.update(overrides)
    return SOAPNote(**defaults)  # type: ignore[arg-type]


class FakeSOAPGeneratorPort(SOAPGeneratorPort):
    def __init__(
        self,
        *,
        raw_text: str = '{"subjective": "Reports headache since yesterday"}',
        session: GenerationSession | None = None,
        error: Exception | None = None,
        stream_chunks: list[SOAPNoteStreamChunk] | None = None,
    ) -> None:
        self._raw_text = raw_text
        self._session = session or make_generation_session()
        self._error = error
        self._stream_chunks = stream_chunks or [SOAPNoteStreamChunk(delta=raw_text, is_final=True)]
        self.received_encounters: list[SOAPEncounterInput] = []

    async def generate(self, encounter: SOAPEncounterInput) -> tuple[str, GenerationSession]:
        self.received_encounters.append(encounter)
        if self._error is not None:
            raise self._error
        return self._raw_text, self._session

    async def stream_generate(
        self, encounter: SOAPEncounterInput
    ) -> AsyncIterator[SOAPNoteStreamChunk]:
        self.received_encounters.append(encounter)
        for chunk in self._stream_chunks:
            yield chunk


class FakeSOAPNoteParserPort(SOAPNoteParserPort):
    def __init__(self, *, result: SOAPNote | None = None, error: Exception | None = None) -> None:
        self._result = result or make_soap_note()
        self._error = error
        self.received: list[tuple[str, SOAPNoteOutputFormat]] = []

    def parse(self, raw_text: str, *, output_format: SOAPNoteOutputFormat) -> SOAPNote:
        self.received.append((raw_text, output_format))
        if self._error is not None:
            raise self._error
        return self._result


class FakeSOAPNoteValidatorPort(SOAPNoteValidatorPort):
    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error
        self.received: list[SOAPNote] = []

    def validate(self, note: SOAPNote) -> None:
        self.received.append(note)
        if self._error is not None:
            raise self._error


class FakeSOAPNoteAuditLoggerPort(SOAPNoteAuditLoggerPort):
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
