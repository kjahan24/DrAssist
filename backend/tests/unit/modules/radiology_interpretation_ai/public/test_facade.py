"""Unit tests for `RadiologyInterpretationAIFacade` — exercised through
`RadiologyInterpretationAIPort` exactly as a future consumer module
would call it, per `docs/backend-architecture/12_testing_architecture.md`'s
"Contract tests" framing."""

from uuid import uuid4

from app.modules.radiology_interpretation_ai.application.services.critical_finding_detection_service import (  # noqa: E501
    CriticalFindingDetectionService,
)
from app.modules.radiology_interpretation_ai.application.services.finding_extraction_service import (  # noqa: E501
    FindingExtractionService,
)
from app.modules.radiology_interpretation_ai.application.services.follow_up_recommendation_service import (  # noqa: E501
    FollowUpRecommendationService,
)
from app.modules.radiology_interpretation_ai.application.services.radiology_summary_service import (  # noqa: E501
    RadiologySummaryService,
)
from app.modules.radiology_interpretation_ai.application.use_cases.interpret_radiology_report import (  # noqa: E501
    InterpretRadiologyReportUseCase,
)
from app.modules.radiology_interpretation_ai.domain.enums import (
    RadiologyExaminationType,
    RadiologyOutputFormat,
    RadiologySetting,
)
from app.modules.radiology_interpretation_ai.public.dto import RadiologyInterpretationInput
from app.modules.radiology_interpretation_ai.public.facade import RadiologyInterpretationAIFacade
from app.modules.radiology_interpretation_ai.public.interfaces import (
    RadiologyInterpretationAIPort,
)
from tests.unit.modules.radiology_interpretation_ai.application.fakes import (
    FakeFindingExtractionPort,
    FakeMedicalReasoningAIPort,
    FakeRadiologyInterpretationAuditLoggerPort,
    FakeRadiologyInterpretationParserPort,
    FakeRadiologyInterpretationValidatorPort,
    FakeRadiologyInterpreterPort,
    make_finding,
    make_result,
)


def _input(**overrides: object) -> RadiologyInterpretationInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "report_text": "The lungs are clear bilaterally. No acute cardiopulmonary abnormality.",
        "examination_type": RadiologyExaminationType.CHEST_XRAY,
        "radiology_setting": RadiologySetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return RadiologyInterpretationInput(**defaults)  # type: ignore[arg-type]


def _facade(
    *,
    generator: FakeRadiologyInterpreterPort | None = None,
    finding_extractor: FakeFindingExtractionPort | None = None,
) -> RadiologyInterpretationAIFacade:
    generator = generator or FakeRadiologyInterpreterPort()
    extractor = finding_extractor or FakeFindingExtractionPort()
    finding_extraction_service = FindingExtractionService(extractor=extractor)
    generate_use_case = InterpretRadiologyReportUseCase(
        generator=generator,
        parser=FakeRadiologyInterpretationParserPort(result=make_result()),
        validator=FakeRadiologyInterpretationValidatorPort(),
        finding_extraction_service=finding_extraction_service,
        critical_finding_service=CriticalFindingDetectionService(extractor=extractor),
        recommendation_service=FollowUpRecommendationService(),
        medical_reasoning=FakeMedicalReasoningAIPort(),
        audit_logger=FakeRadiologyInterpretationAuditLoggerPort(),
    )
    return RadiologyInterpretationAIFacade(
        generate_use_case=generate_use_case,
        finding_extraction_service=finding_extraction_service,
        summary_service=RadiologySummaryService(),
        generator=generator,
    )


class TestRadiologyInterpretationAIFacade:
    def test_is_a_radiology_interpretation_ai_port(self) -> None:
        assert isinstance(_facade(), RadiologyInterpretationAIPort)

    async def test_generate_interpretation_delegates_to_the_use_case(self) -> None:
        facade = _facade()

        generated = await facade.generate_interpretation(_input())

        assert generated.result is not None
        assert generated.session is not None

    async def test_stream_generate_interpretation_delegates_to_the_generator(self) -> None:
        generator = FakeRadiologyInterpreterPort(raw_text="hello world")
        facade = _facade(generator=generator)

        chunks = [chunk async for chunk in facade.stream_generate_interpretation(_input())]

        assert "".join(c.delta for c in chunks) == "hello world"

    async def test_render_result_delegates_to_the_summary_service(self) -> None:
        facade = _facade()
        result = make_result()

        rendered = await facade.render_result(result, target_format=RadiologyOutputFormat.TEXT)

        assert "EXAMINATION SUMMARY:" in rendered

    def test_extract_candidate_findings_delegates_to_the_finding_extraction_service(self) -> None:
        candidates = (make_finding(description="Pneumothorax"),)
        extractor = FakeFindingExtractionPort(candidates=candidates)
        facade = _facade(finding_extractor=extractor)

        result = facade.extract_candidate_findings("some report text")

        assert result == candidates
