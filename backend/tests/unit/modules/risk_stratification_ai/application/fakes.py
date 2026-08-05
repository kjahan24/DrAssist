"""In-memory test doubles for the AI Risk Stratification & Early
Warning Score module's application-layer ports, plus a fake AI
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
from app.modules.risk_stratification_ai.application.ports import (
    ClinicalRiskPort,
    EarlyWarningPort,
    RiskScoringPort,
    RiskStratificationAnalysisAuditLoggerPort,
    RiskStratificationAnalysisGeneratorPort,
    RiskStratificationAnalysisParserPort,
    RiskStratificationAnalysisValidatorPort,
)
from app.modules.risk_stratification_ai.domain.enums import (
    OverallRiskLevel,
    RiskAnalysisStatus,
    RiskCategory,
    RiskStratificationOutputFormat,
    RiskStratificationSetting,
)
from app.modules.risk_stratification_ai.domain.value_objects import (
    GenerationSession,
    LabValue,
    RiskScore,
    RiskStratificationInput,
    RiskStratificationResult,
    RiskStratificationStreamChunk,
    VitalSigns,
)


def make_generation_session(**overrides: object) -> GenerationSession:
    defaults: dict[str, object] = {
        "generation_id": uuid4(),
        "provider": "mock",
        "model": "mock-model",
        "risk_setting": "outpatient",
        "language": "en",
        "status": RiskAnalysisStatus.COMPLETED,
        "latency_ms": 1.0,
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
        "estimated_cost_usd": 0.0001,
    }
    defaults.update(overrides)
    return GenerationSession(**defaults)  # type: ignore[arg-type]


def make_vital_signs(**overrides: object) -> VitalSigns:
    defaults: dict[str, object] = {
        "respiratory_rate": 16,
        "oxygen_saturation": 97.0,
        "on_supplemental_oxygen": False,
        "temperature_celsius": 37.0,
        "systolic_bp": 120,
        "diastolic_bp": 80,
        "heart_rate": 78,
        "consciousness_level": None,
    }
    defaults.update(overrides)
    return VitalSigns(**defaults)  # type: ignore[arg-type]


def make_lab_value(**overrides: object) -> LabValue:
    defaults: dict[str, object] = {"test_name": "Creatinine", "numeric_value": 1.0}
    defaults.update(overrides)
    return LabValue(**defaults)  # type: ignore[arg-type]


def make_risk_score(**overrides: object) -> RiskScore:
    defaults: dict[str, object] = {
        "category": RiskCategory.NEWS2,
        "score_value": 3.0,
        "contributing_factors": ("Respiratory rate 22/min (elevated)",),
        "clinical_explanation": "NEWS2 score of 3.",
    }
    defaults.update(overrides)
    return RiskScore(**defaults)  # type: ignore[arg-type]


def make_result(**overrides: object) -> RiskStratificationResult:
    defaults: dict[str, object] = {
        "overall_risk_level": OverallRiskLevel.MODERATE,
        "risk_scores": (make_risk_score(),),
        "early_warning_indicators": (),
        "recommended_monitoring": (),
        "suggested_escalation": (),
        "suggested_follow_up": (),
        "red_flag_alerts": (),
        "clinical_reasoning": "Grounded in the reported vital signs.",
        "confidence_score": 0.8,
        "raw_text": '{"overall_risk_level": "moderate"}',
        "output_format": RiskStratificationOutputFormat.JSON,
    }
    defaults.update(overrides)
    return RiskStratificationResult(**defaults)  # type: ignore[arg-type]


def make_input(**overrides: object) -> RiskStratificationInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "risk_setting": RiskStratificationSetting.OUTPATIENT,
        "vital_signs": make_vital_signs(),
    }
    defaults.update(overrides)
    return RiskStratificationInput(**defaults)  # type: ignore[arg-type]


class FakeRiskStratificationAnalysisGeneratorPort(RiskStratificationAnalysisGeneratorPort):
    def __init__(
        self,
        *,
        raw_text: str = '{"overall_risk_level": "moderate"}',
        session: GenerationSession | None = None,
        error: Exception | None = None,
        stream_chunks: list[RiskStratificationStreamChunk] | None = None,
    ) -> None:
        self._raw_text = raw_text
        self._session = session or make_generation_session()
        self._error = error
        self._stream_chunks = stream_chunks or [
            RiskStratificationStreamChunk(delta=raw_text, is_final=True)
        ]
        self.received: list[RiskStratificationInput] = []

    async def generate(self, input_dto: RiskStratificationInput) -> tuple[str, GenerationSession]:
        self.received.append(input_dto)
        if self._error is not None:
            raise self._error
        return self._raw_text, self._session

    async def stream_generate(
        self, input_dto: RiskStratificationInput
    ) -> AsyncIterator[RiskStratificationStreamChunk]:
        self.received.append(input_dto)
        for chunk in self._stream_chunks:
            yield chunk


class FakeRiskStratificationAnalysisParserPort(RiskStratificationAnalysisParserPort):
    def __init__(
        self,
        *,
        result: RiskStratificationResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result or make_result()
        self._error = error
        self.received: list[tuple[str, RiskStratificationOutputFormat]] = []

    def parse(
        self, raw_text: str, *, output_format: RiskStratificationOutputFormat
    ) -> RiskStratificationResult:
        self.received.append((raw_text, output_format))
        if self._error is not None:
            raise self._error
        return self._result


class FakeRiskStratificationAnalysisValidatorPort(RiskStratificationAnalysisValidatorPort):
    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error
        self.received: list[tuple[RiskStratificationResult, RiskStratificationInput]] = []

    def validate(
        self, result: RiskStratificationResult, input_dto: RiskStratificationInput
    ) -> None:
        self.received.append((result, input_dto))
        if self._error is not None:
            raise self._error


class FakeRiskStratificationAnalysisAuditLoggerPort(RiskStratificationAnalysisAuditLoggerPort):
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


class FakeRiskScoringPort(RiskScoringPort):
    def __init__(
        self,
        *,
        news2: RiskScore | None = None,
        mews: RiskScore | None = None,
        qsofa: RiskScore | None = None,
        sofa_simplified: RiskScore | None = None,
    ) -> None:
        self._news2 = news2
        self._mews = mews
        self._qsofa = qsofa
        self._sofa_simplified = sofa_simplified
        self.calls: list[str] = []

    def compute_news2(self, vital_signs: VitalSigns) -> RiskScore | None:
        self.calls.append("news2")
        return self._news2

    def compute_mews(self, vital_signs: VitalSigns) -> RiskScore | None:
        self.calls.append("mews")
        return self._mews

    def compute_qsofa(self, vital_signs: VitalSigns) -> RiskScore | None:
        self.calls.append("qsofa")
        return self._qsofa

    def compute_sofa_simplified(
        self, vital_signs: VitalSigns, lab_values: tuple[LabValue, ...]
    ) -> RiskScore | None:
        self.calls.append("sofa_simplified")
        return self._sofa_simplified


class FakeEarlyWarningPort(EarlyWarningPort):
    def __init__(
        self,
        *,
        triggers: tuple[str, ...] = (),
        escalation_by_category: dict[RiskCategory, str] | None = None,
    ) -> None:
        self._triggers = triggers
        self._escalation_by_category = escalation_by_category or {}
        self.trigger_calls: list[VitalSigns] = []
        self.escalation_calls: list[RiskScore] = []

    def identify_single_parameter_triggers(self, vital_signs: VitalSigns) -> tuple[str, ...]:
        self.trigger_calls.append(vital_signs)
        return self._triggers

    def classify_escalation_urgency(self, risk_score: RiskScore) -> str | None:
        self.escalation_calls.append(risk_score)
        return self._escalation_by_category.get(risk_score.category)


class FakeClinicalRiskPort(ClinicalRiskPort):
    def __init__(self, *, score: RiskScore | None = None) -> None:
        self._score = score
        self.calls: list[RiskCategory] = []

    def identify_risk_factors(
        self,
        category: RiskCategory,
        *,
        diagnoses: tuple[str, ...],
        medical_history: tuple[str, ...],
        current_medications: tuple[str, ...],
        lab_values: tuple[LabValue, ...],
        patient_age: int | None,
    ) -> RiskScore | None:
        self.calls.append(category)
        return self._score


class FakeMedicalReasoningAIPort(MedicalReasoningAIPort):
    def __init__(self, *, confidence_value: float = 0.55) -> None:
        self._confidence_value = confidence_value
        self.score_confidence_calls: list[dict[str, object]] = []

    async def generate_reasoning(
        self, evidence: MedicalReasoningInput
    ) -> GeneratedMedicalReasoning:
        raise NotImplementedError("not exercised by risk_stratification_ai's own tests")

    def stream_generate_reasoning(
        self, evidence: MedicalReasoningInput
    ) -> AsyncIterator[MedicalReasoningStreamChunk]:
        raise NotImplementedError("not exercised by risk_stratification_ai's own tests")

    async def render_result(
        self, result: MedicalReasoningResult, *, target_format: MedicalReasoningOutputFormat
    ) -> str:
        raise NotImplementedError("not exercised by risk_stratification_ai's own tests")

    def weight_evidence(self, items: tuple[EvidenceItem, ...]) -> tuple[EvidenceItem, ...]:
        raise NotImplementedError("not exercised by risk_stratification_ai's own tests")

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
