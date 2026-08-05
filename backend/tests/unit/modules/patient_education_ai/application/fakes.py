"""In-memory test doubles for the AI Patient Education & Discharge
Instructions module's application-layer ports, plus a fake AI
Foundation `AIGatewayPort` and a fake peer-module `MedicalReasoningAIPort`
for infrastructure/use-case-level tests — per `docs/backend-architecture
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
from app.modules.medical_reasoning_ai.public.dto import (
    EvidenceItem,
    GeneratedMedicalReasoning,
    MedicalReasoningInput,
    MedicalReasoningOutputFormat,
    MedicalReasoningResult,
    MedicalReasoningStreamChunk,
)
from app.modules.medical_reasoning_ai.public.interfaces import MedicalReasoningAIPort
from app.modules.patient_education_ai.application.ports import (
    DischargeInstructionPort,
    LifestyleRecommendationPort,
    PatientEducationAnalysisAuditLoggerPort,
    PatientEducationAnalysisGeneratorPort,
    PatientEducationAnalysisParserPort,
    PatientEducationAnalysisValidatorPort,
    PatientEducationPort,
)
from app.modules.patient_education_ai.domain.enums import (
    EducationGenerationStatus,
    PatientEducationOutputFormat,
    PatientEducationSetting,
)
from app.modules.patient_education_ai.domain.value_objects import (
    GenerationSession,
    PatientEducationInput,
    PatientEducationResult,
    PatientEducationStreamChunk,
)


def make_generation_session(**overrides: object) -> GenerationSession:
    defaults: dict[str, object] = {
        "generation_id": uuid4(),
        "provider": "mock",
        "model": "mock-model",
        "education_setting": "adult",
        "language": "en",
        "status": EducationGenerationStatus.COMPLETED,
        "latency_ms": 1.0,
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
        "estimated_cost_usd": 0.0001,
    }
    defaults.update(overrides)
    return GenerationSession(**defaults)  # type: ignore[arg-type]


def make_result(**overrides: object) -> PatientEducationResult:
    defaults: dict[str, object] = {
        "patient_summary": "You were seen today and your care plan is summarized below.",
        "diagnosis_explanation": "Your diagnosis is explained in plain language.",
        "medication_instructions": (),
        "home_care_plan": (),
        "lifestyle_advice": (),
        "diet_advice": (),
        "exercise_advice": (),
        "warning_signs": (),
        "emergency_instructions": (),
        "follow_up_plan": (),
        "patient_checklist": (),
        "confidence_score": 0.8,
        "raw_text": '{"patient_summary": "You were seen today."}',
        "output_format": PatientEducationOutputFormat.JSON,
    }
    defaults.update(overrides)
    return PatientEducationResult(**defaults)  # type: ignore[arg-type]


def make_input(**overrides: object) -> PatientEducationInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "education_setting": PatientEducationSetting.ADULT,
        "diagnoses": ("Hypertension",),
        "current_medications": ("Lisinopril",),
    }
    defaults.update(overrides)
    return PatientEducationInput(**defaults)  # type: ignore[arg-type]


class FakePatientEducationAnalysisGeneratorPort(PatientEducationAnalysisGeneratorPort):
    def __init__(
        self,
        *,
        raw_text: str = '{"patient_summary": "You were seen today."}',
        session: GenerationSession | None = None,
        error: Exception | None = None,
        stream_chunks: list[PatientEducationStreamChunk] | None = None,
    ) -> None:
        self._raw_text = raw_text
        self._session = session or make_generation_session()
        self._error = error
        self._stream_chunks = stream_chunks or [
            PatientEducationStreamChunk(delta=raw_text, is_final=True)
        ]
        self.received: list[PatientEducationInput] = []

    async def generate(self, input_dto: PatientEducationInput) -> tuple[str, GenerationSession]:
        self.received.append(input_dto)
        if self._error is not None:
            raise self._error
        return self._raw_text, self._session

    async def stream_generate(
        self, input_dto: PatientEducationInput
    ) -> AsyncIterator[PatientEducationStreamChunk]:
        self.received.append(input_dto)
        for chunk in self._stream_chunks:
            yield chunk


class FakePatientEducationAnalysisParserPort(PatientEducationAnalysisParserPort):
    def __init__(
        self,
        *,
        result: PatientEducationResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result or make_result()
        self._error = error
        self.received: list[tuple[str, PatientEducationOutputFormat]] = []

    def parse(
        self, raw_text: str, *, output_format: PatientEducationOutputFormat
    ) -> PatientEducationResult:
        self.received.append((raw_text, output_format))
        if self._error is not None:
            raise self._error
        return self._result


class FakePatientEducationAnalysisValidatorPort(PatientEducationAnalysisValidatorPort):
    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error
        self.received: list[tuple[PatientEducationResult, PatientEducationInput]] = []

    def validate(self, result: PatientEducationResult, input_dto: PatientEducationInput) -> None:
        self.received.append((result, input_dto))
        if self._error is not None:
            raise self._error


class FakePatientEducationAnalysisAuditLoggerPort(PatientEducationAnalysisAuditLoggerPort):
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


class FakePatientEducationPort(PatientEducationPort):
    def __init__(
        self,
        *,
        explanation: str | None = None,
        warning_signs: tuple[str, ...] = (),
        emergency_symptoms: tuple[str, ...] = (),
    ) -> None:
        self._explanation = explanation
        self._warning_signs = warning_signs
        self._emergency_symptoms = emergency_symptoms
        self.explain_calls: list[str] = []
        self.warning_signs_calls: list[str] = []
        self.emergency_symptoms_calls: list[str] = []

    def explain_diagnosis(self, diagnosis: str) -> str | None:
        self.explain_calls.append(diagnosis)
        return self._explanation

    def identify_warning_signs(self, diagnosis: str) -> tuple[str, ...]:
        self.warning_signs_calls.append(diagnosis)
        return self._warning_signs

    def identify_emergency_symptoms(self, diagnosis: str) -> tuple[str, ...]:
        self.emergency_symptoms_calls.append(diagnosis)
        return self._emergency_symptoms


class FakeDischargeInstructionPort(DischargeInstructionPort):
    def __init__(
        self,
        *,
        medication_instruction: str | None = None,
        home_care_instructions: tuple[str, ...] = (),
        discharge_checklist: tuple[str, ...] = (),
    ) -> None:
        self._medication_instruction = medication_instruction
        self._home_care_instructions = home_care_instructions
        self._discharge_checklist = discharge_checklist
        self.instruct_medication_calls: list[str] = []

    def instruct_medication(self, medication: str) -> str | None:
        self.instruct_medication_calls.append(medication)
        return self._medication_instruction

    def generate_home_care_instructions(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]:
        return self._home_care_instructions

    def generate_discharge_checklist(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]:
        return self._discharge_checklist


class FakeLifestyleRecommendationPort(LifestyleRecommendationPort):
    def __init__(
        self,
        *,
        lifestyle: tuple[str, ...] = (),
        diet: tuple[str, ...] = (),
        exercise: tuple[str, ...] = (),
        preventive_care: tuple[str, ...] = (),
    ) -> None:
        self._lifestyle = lifestyle
        self._diet = diet
        self._exercise = exercise
        self._preventive_care = preventive_care
        self.preventive_care_calls: list[tuple[tuple[str, ...], int | None]] = []

    def recommend_lifestyle(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]:
        return self._lifestyle

    def recommend_diet(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]:
        return self._diet

    def recommend_exercise(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]:
        return self._exercise

    def recommend_preventive_care(
        self, diagnoses: tuple[str, ...], patient_age: int | None
    ) -> tuple[str, ...]:
        self.preventive_care_calls.append((diagnoses, patient_age))
        return self._preventive_care


class FakeMedicalReasoningAIPort(MedicalReasoningAIPort):
    def __init__(self, *, confidence_value: float = 0.55) -> None:
        self._confidence_value = confidence_value
        self.score_confidence_calls: list[dict[str, object]] = []

    async def generate_reasoning(
        self, evidence: MedicalReasoningInput
    ) -> GeneratedMedicalReasoning:
        raise NotImplementedError("not exercised by patient_education_ai's own tests")

    def stream_generate_reasoning(
        self, evidence: MedicalReasoningInput
    ) -> AsyncIterator[MedicalReasoningStreamChunk]:
        raise NotImplementedError("not exercised by patient_education_ai's own tests")

    async def render_result(
        self, result: MedicalReasoningResult, *, target_format: MedicalReasoningOutputFormat
    ) -> str:
        raise NotImplementedError("not exercised by patient_education_ai's own tests")

    def weight_evidence(self, items: tuple[EvidenceItem, ...]) -> tuple[EvidenceItem, ...]:
        raise NotImplementedError("not exercised by patient_education_ai's own tests")

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
