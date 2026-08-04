"""Unit tests for `MedicalReasoningAIFacade` — exercised through
`MedicalReasoningAIPort` exactly as a future consumer module would call
it, per `docs/backend-architecture/12_testing_architecture.md`'s
"Contract tests" framing."""

from uuid import uuid4

from app.modules.medical_reasoning_ai.application.services.clinical_summary_service import (
    ClinicalSummaryService,
)
from app.modules.medical_reasoning_ai.application.services.confidence_scoring_service import (
    ConfidenceScoringService,
)
from app.modules.medical_reasoning_ai.application.services.evidence_analysis_service import (
    EvidenceAnalysisService,
)
from app.modules.medical_reasoning_ai.application.services.recommendation_reasoning_service import (
    RecommendationReasoningService,
)
from app.modules.medical_reasoning_ai.application.use_cases.generate_clinical_reasoning import (
    GenerateClinicalReasoningUseCase,
)
from app.modules.medical_reasoning_ai.domain.enums import (
    MedicalReasoningOutputFormat,
    ReasoningSetting,
)
from app.modules.medical_reasoning_ai.public.dto import MedicalReasoningInput
from app.modules.medical_reasoning_ai.public.facade import MedicalReasoningAIFacade
from app.modules.medical_reasoning_ai.public.interfaces import MedicalReasoningAIPort
from tests.unit.modules.medical_reasoning_ai.application.fakes import (
    FakeConfidenceCalculatorPort,
    FakeEvidenceAnalyzerPort,
    FakeMedicalReasoningAuditLoggerPort,
    FakeMedicalReasoningParserPort,
    FakeMedicalReasoningPort,
    FakeMedicalReasoningValidatorPort,
    make_evidence_item,
    make_result,
)


def _evidence(**overrides: object) -> MedicalReasoningInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Chest pain",
        "reasoning_setting": ReasoningSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return MedicalReasoningInput(**defaults)  # type: ignore[arg-type]


def _facade(*, generator: FakeMedicalReasoningPort | None = None) -> MedicalReasoningAIFacade:
    generator = generator or FakeMedicalReasoningPort()
    evidence_service = EvidenceAnalysisService(analyzer=FakeEvidenceAnalyzerPort())
    confidence_service = ConfidenceScoringService(calculator=FakeConfidenceCalculatorPort())
    recommendation_service = RecommendationReasoningService()
    generate_use_case = GenerateClinicalReasoningUseCase(
        generator=generator,
        parser=FakeMedicalReasoningParserPort(result=make_result()),
        validator=FakeMedicalReasoningValidatorPort(),
        evidence_service=evidence_service,
        confidence_service=confidence_service,
        recommendation_service=recommendation_service,
        audit_logger=FakeMedicalReasoningAuditLoggerPort(),
    )
    return MedicalReasoningAIFacade(
        generate_use_case=generate_use_case,
        evidence_service=evidence_service,
        confidence_service=confidence_service,
        summary_service=ClinicalSummaryService(),
        generator=generator,
    )


class TestMedicalReasoningAIFacade:
    def test_is_a_medical_reasoning_ai_port(self) -> None:
        assert isinstance(_facade(), MedicalReasoningAIPort)

    async def test_generate_reasoning_delegates_to_the_use_case(self) -> None:
        facade = _facade()

        result = await facade.generate_reasoning(_evidence())

        assert result.result is not None
        assert result.session is not None

    async def test_stream_generate_reasoning_delegates_to_the_generator(self) -> None:
        generator = FakeMedicalReasoningPort(raw_text="hello world")
        facade = _facade(generator=generator)

        chunks = [chunk async for chunk in facade.stream_generate_reasoning(_evidence())]

        assert "".join(c.delta for c in chunks) == "hello world"

    async def test_render_result_delegates_to_the_summary_service(self) -> None:
        facade = _facade()
        result = make_result()

        rendered = await facade.render_result(
            result, target_format=MedicalReasoningOutputFormat.TEXT
        )

        assert "CLINICAL SUMMARY:" in rendered

    def test_weight_evidence_delegates_to_the_evidence_service(self) -> None:
        facade = _facade()
        items = (make_evidence_item(weight=0.5),)

        weighted = facade.weight_evidence(items)

        assert len(weighted) == 1

    def test_score_confidence_delegates_to_the_confidence_service(self) -> None:
        facade = _facade()

        score = facade.score_confidence(
            ai_reported=0.9,
            supporting_count=1,
            contradicting_count=0,
            missing_information_count=0,
        )

        assert score == 0.9
