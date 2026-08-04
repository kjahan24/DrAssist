"""In-memory test doubles for the AI Prescription Assistance module's
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
from app.modules.prescription_ai.application.ports import (
    DrugInteractionPort,
    MedicationKnowledgePort,
    PrescriptionAuditLoggerPort,
    PrescriptionGeneratorPort,
    PrescriptionSuggestionParserPort,
    PrescriptionSuggestionValidatorPort,
)
from app.modules.prescription_ai.domain.enums import (
    AdministrationRoute,
    GenerationStatus,
    PrescriptionOutputFormat,
)
from app.modules.prescription_ai.domain.value_objects import (
    GenerationSession,
    MedicationSafetyFinding,
    MedicationSuggestion,
    PrescriptionContextInput,
    PrescriptionStreamChunk,
    PrescriptionSuggestionSet,
)


def make_generation_session(**overrides: object) -> GenerationSession:
    defaults: dict[str, object] = {
        "generation_id": uuid4(),
        "provider": "mock",
        "model": "mock-model",
        "prescribing_setting": "outpatient",
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


def make_medication(**overrides: object) -> MedicationSuggestion:
    defaults: dict[str, object] = {
        "generic_name": "amoxicillin",
        "brand_name": None,
        "strength": "500mg",
        "dosage": "1 capsule",
        "route": AdministrationRoute.ORAL,
        "frequency": "three times daily",
        "duration": "7 days",
        "quantity": "21 capsules",
        "is_prn": False,
        "clinical_indication": "Acute pharyngitis",
        "monitoring_advice": "Watch for rash",
        "patient_instructions": "Take with food",
        "confidence_score": 0.85,
        "clinical_reasoning": "First-line for bacterial pharyngitis",
    }
    defaults.update(overrides)
    return MedicationSuggestion(**defaults)  # type: ignore[arg-type]


def make_suggestion_set(**overrides: object) -> PrescriptionSuggestionSet:
    defaults: dict[str, object] = {
        "medications": (make_medication(),),
        "safety_findings": (),
        "monitoring_recommendations": (),
        "follow_up_recommendations": (),
        "raw_text": '{"medications": [{"generic_name": "amoxicillin"}]}',
        "output_format": PrescriptionOutputFormat.JSON,
    }
    defaults.update(overrides)
    return PrescriptionSuggestionSet(**defaults)  # type: ignore[arg-type]


class FakePrescriptionGeneratorPort(PrescriptionGeneratorPort):
    def __init__(
        self,
        *,
        raw_text: str = '{"medications": [{"generic_name": "amoxicillin"}]}',
        session: GenerationSession | None = None,
        error: Exception | None = None,
        stream_chunks: list[PrescriptionStreamChunk] | None = None,
    ) -> None:
        self._raw_text = raw_text
        self._session = session or make_generation_session()
        self._error = error
        self._stream_chunks = stream_chunks or [
            PrescriptionStreamChunk(delta=raw_text, is_final=True)
        ]
        self.received_contexts: list[PrescriptionContextInput] = []

    async def generate(self, context: PrescriptionContextInput) -> tuple[str, GenerationSession]:
        self.received_contexts.append(context)
        if self._error is not None:
            raise self._error
        return self._raw_text, self._session

    async def stream_generate(
        self, context: PrescriptionContextInput
    ) -> AsyncIterator[PrescriptionStreamChunk]:
        self.received_contexts.append(context)
        for chunk in self._stream_chunks:
            yield chunk


class FakePrescriptionSuggestionParserPort(PrescriptionSuggestionParserPort):
    def __init__(
        self, *, result: PrescriptionSuggestionSet | None = None, error: Exception | None = None
    ) -> None:
        self._result = result or make_suggestion_set()
        self._error = error
        self.received: list[tuple[str, PrescriptionOutputFormat]] = []

    def parse(
        self, raw_text: str, *, output_format: PrescriptionOutputFormat
    ) -> PrescriptionSuggestionSet:
        self.received.append((raw_text, output_format))
        if self._error is not None:
            raise self._error
        return self._result


class FakePrescriptionSuggestionValidatorPort(PrescriptionSuggestionValidatorPort):
    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error
        self.received: list[PrescriptionSuggestionSet] = []

    def validate(self, suggestion_set: PrescriptionSuggestionSet) -> None:
        self.received.append(suggestion_set)
        if self._error is not None:
            raise self._error


class FakePrescriptionAuditLoggerPort(PrescriptionAuditLoggerPort):
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


class FakeMedicationKnowledgePort(MedicationKnowledgePort):
    def __init__(self, *, therapeutic_classes: dict[str, str] | None = None) -> None:
        self._therapeutic_classes = therapeutic_classes or {}
        self.class_lookups: list[str] = []

    def is_known_medication(self, generic_name: str) -> bool:
        return generic_name.strip().lower() in self._therapeutic_classes

    def lookup_therapeutic_class(self, generic_name: str) -> str | None:
        self.class_lookups.append(generic_name)
        return self._therapeutic_classes.get(generic_name.strip().lower())


class FakeDrugInteractionPort(DrugInteractionPort):
    def __init__(
        self,
        *,
        interaction_findings: tuple[MedicationSafetyFinding, ...] = (),
        allergy_findings: tuple[MedicationSafetyFinding, ...] = (),
    ) -> None:
        self._interaction_findings = interaction_findings
        self._allergy_findings = allergy_findings
        self.interaction_calls: list[tuple[str, ...]] = []
        self.allergy_calls: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

    def check_interactions(
        self, generic_names: tuple[str, ...]
    ) -> tuple[MedicationSafetyFinding, ...]:
        self.interaction_calls.append(generic_names)
        return self._interaction_findings

    def check_allergy_conflicts(
        self, generic_names: tuple[str, ...], allergies: tuple[str, ...]
    ) -> tuple[MedicationSafetyFinding, ...]:
        self.allergy_calls.append((generic_names, allergies))
        return self._allergy_findings


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
