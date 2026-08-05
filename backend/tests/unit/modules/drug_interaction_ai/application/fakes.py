"""In-memory test doubles for the AI Drug Interaction & Medication
Safety module's application-layer ports, plus a fake AI Foundation
`AIGatewayPort` and a fake peer-module `MedicalReasoningAIPort` for
infrastructure/use-case-level tests — per `docs/backend-architecture
/12_testing_architecture.md` ("fakes over mocks as the default").
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
from app.modules.drug_interaction_ai.application.ports import (
    DoseAdjustmentPort,
    DrugInteractionPort,
    DrugSafetyAnalysisAuditLoggerPort,
    DrugSafetyAnalysisGeneratorPort,
    DrugSafetyAnalysisParserPort,
    DrugSafetyAnalysisValidatorPort,
    InteractionEvidencePort,
    MedicationSafetyPort,
)
from app.modules.drug_interaction_ai.domain.enums import (
    DrugInteractionOutputFormat,
    EvidenceLevel,
    LactationStatus,
    PregnancyStatus,
    SafetyAnalysisStatus,
    SafetyIssueCategory,
    SafetySeverity,
)
from app.modules.drug_interaction_ai.domain.value_objects import (
    DrugInteractionAnalysisInput,
    DrugInteractionAnalysisResult,
    DrugInteractionStreamChunk,
    GenerationSession,
    MedicationEntry,
    SafetyIssue,
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


def make_generation_session(**overrides: object) -> GenerationSession:
    defaults: dict[str, object] = {
        "generation_id": uuid4(),
        "provider": "mock",
        "model": "mock-model",
        "medication_setting": "outpatient",
        "language": "en",
        "status": SafetyAnalysisStatus.COMPLETED,
        "latency_ms": 1.0,
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
        "estimated_cost_usd": 0.0001,
    }
    defaults.update(overrides)
    return GenerationSession(**defaults)  # type: ignore[arg-type]


def make_medication(**overrides: object) -> MedicationEntry:
    defaults: dict[str, object] = {"drug_name": "Warfarin"}
    defaults.update(overrides)
    return MedicationEntry(**defaults)  # type: ignore[arg-type]


def make_issue(**overrides: object) -> SafetyIssue:
    defaults: dict[str, object] = {
        "category": SafetyIssueCategory.DRUG_DRUG_INTERACTION,
        "description": "Warfarin and Aspirin increase bleeding risk",
        "severity": SafetySeverity.MODERATE,
        "involved_medications": ("Warfarin", "Aspirin"),
    }
    defaults.update(overrides)
    return SafetyIssue(**defaults)  # type: ignore[arg-type]


def make_result(**overrides: object) -> DrugInteractionAnalysisResult:
    defaults: dict[str, object] = {
        "safety_summary": "Medication list reviewed, one moderate interaction identified.",
        "interactions": (make_issue(),),
        "contraindications": (),
        "warnings": (),
        "monitoring_recommendations": (),
        "dose_adjustment_suggestions": (),
        "alternative_medication_suggestions": (),
        "patient_counseling_points": (),
        "clinical_reasoning": "Grounded in the reported medication list.",
        "confidence_score": 0.8,
        "raw_text": '{"safety_summary": "Medication list reviewed."}',
        "output_format": DrugInteractionOutputFormat.JSON,
    }
    defaults.update(overrides)
    return DrugInteractionAnalysisResult(**defaults)  # type: ignore[arg-type]


def make_input(**overrides: object) -> DrugInteractionAnalysisInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "medication_setting": "outpatient",
        "current_medications": (make_medication(),),
    }
    defaults.update(overrides)
    return DrugInteractionAnalysisInput(**defaults)  # type: ignore[arg-type]


class FakeDrugSafetyAnalysisGeneratorPort(DrugSafetyAnalysisGeneratorPort):
    def __init__(
        self,
        *,
        raw_text: str = '{"safety_summary": "Medication list reviewed."}',
        session: GenerationSession | None = None,
        error: Exception | None = None,
        stream_chunks: list[DrugInteractionStreamChunk] | None = None,
    ) -> None:
        self._raw_text = raw_text
        self._session = session or make_generation_session()
        self._error = error
        self._stream_chunks = stream_chunks or [
            DrugInteractionStreamChunk(delta=raw_text, is_final=True)
        ]
        self.received: list[DrugInteractionAnalysisInput] = []

    async def generate(
        self, input_dto: DrugInteractionAnalysisInput
    ) -> tuple[str, GenerationSession]:
        self.received.append(input_dto)
        if self._error is not None:
            raise self._error
        return self._raw_text, self._session

    async def stream_generate(
        self, input_dto: DrugInteractionAnalysisInput
    ) -> AsyncIterator[DrugInteractionStreamChunk]:
        self.received.append(input_dto)
        for chunk in self._stream_chunks:
            yield chunk


class FakeDrugSafetyAnalysisParserPort(DrugSafetyAnalysisParserPort):
    def __init__(
        self,
        *,
        result: DrugInteractionAnalysisResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result or make_result()
        self._error = error
        self.received: list[tuple[str, DrugInteractionOutputFormat]] = []

    def parse(
        self, raw_text: str, *, output_format: DrugInteractionOutputFormat
    ) -> DrugInteractionAnalysisResult:
        self.received.append((raw_text, output_format))
        if self._error is not None:
            raise self._error
        return self._result


class FakeDrugSafetyAnalysisValidatorPort(DrugSafetyAnalysisValidatorPort):
    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error
        self.received: list[tuple[DrugInteractionAnalysisResult, DrugInteractionAnalysisInput]] = []

    def validate(
        self, result: DrugInteractionAnalysisResult, input_dto: DrugInteractionAnalysisInput
    ) -> None:
        self.received.append((result, input_dto))
        if self._error is not None:
            raise self._error


class FakeDrugSafetyAnalysisAuditLoggerPort(DrugSafetyAnalysisAuditLoggerPort):
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


class FakeDrugInteractionPort(DrugInteractionPort):
    def __init__(self, *, issue: SafetyIssue | None = None) -> None:
        self._issue = issue
        self.calls: list[tuple[str, str]] = []

    def check_pairwise_interaction(self, drug_a: str, drug_b: str) -> SafetyIssue | None:
        self.calls.append((drug_a, drug_b))
        return self._issue


class FakeInteractionEvidencePort(InteractionEvidencePort):
    def __init__(self, *, evidence_level: EvidenceLevel | None = None) -> None:
        self._evidence_level = evidence_level
        self.calls: list[tuple[str, str]] = []

    def classify_evidence_level(self, drug_a: str, drug_b: str) -> EvidenceLevel | None:
        self.calls.append((drug_a, drug_b))
        return self._evidence_level


class FakeMedicationSafetyPort(MedicationSafetyPort):
    def __init__(
        self,
        *,
        context_risks: tuple[SafetyIssue, ...] = (),
        risk_flags: tuple[SafetyIssueCategory, ...] = (),
        contraindication: str | None = None,
        black_box_warning: str | None = None,
    ) -> None:
        self._context_risks = context_risks
        self._risk_flags = risk_flags
        self._contraindication = contraindication
        self._black_box_warning = black_box_warning
        self.context_risk_calls: list[MedicationEntry] = []
        self.risk_flag_calls: list[MedicationEntry] = []

    def check_patient_context_risks(
        self,
        medication: MedicationEntry,
        *,
        allergies: tuple[str, ...],
        medical_conditions: tuple[str, ...],
        pregnancy_status: PregnancyStatus | None,
        lactation_status: LactationStatus | None,
        patient_age: int | None,
    ) -> tuple[SafetyIssue, ...]:
        self.context_risk_calls.append(medication)
        return self._context_risks

    def classify_pharmacologic_risk_flags(
        self, medication: MedicationEntry
    ) -> tuple[SafetyIssueCategory, ...]:
        self.risk_flag_calls.append(medication)
        return self._risk_flags

    def check_contraindication(self, medication: MedicationEntry) -> str | None:
        return self._contraindication

    def check_black_box_warning(self, medication: MedicationEntry) -> str | None:
        return self._black_box_warning


class FakeDoseAdjustmentPort(DoseAdjustmentPort):
    def __init__(self, *, suggestion: str | None = None) -> None:
        self._suggestion = suggestion
        self.calls: list[MedicationEntry] = []

    def suggest_dose_adjustment(
        self,
        medication: MedicationEntry,
        *,
        renal_function: str | None,
        hepatic_function: str | None,
    ) -> str | None:
        self.calls.append(medication)
        return self._suggestion


class FakeMedicalReasoningAIPort(MedicalReasoningAIPort):
    def __init__(self, *, confidence_value: float = 0.55) -> None:
        self._confidence_value = confidence_value
        self.score_confidence_calls: list[dict[str, object]] = []

    async def generate_reasoning(
        self, evidence: MedicalReasoningInput
    ) -> GeneratedMedicalReasoning:
        raise NotImplementedError("not exercised by drug_interaction_ai's own tests")

    def stream_generate_reasoning(
        self, evidence: MedicalReasoningInput
    ) -> AsyncIterator[MedicalReasoningStreamChunk]:
        raise NotImplementedError("not exercised by drug_interaction_ai's own tests")

    async def render_result(
        self, result: MedicalReasoningResult, *, target_format: MedicalReasoningOutputFormat
    ) -> str:
        raise NotImplementedError("not exercised by drug_interaction_ai's own tests")

    def weight_evidence(self, items: tuple[EvidenceItem, ...]) -> tuple[EvidenceItem, ...]:
        raise NotImplementedError("not exercised by drug_interaction_ai's own tests")

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
