"""Unit tests for `PathologyInterpretationAIFacade` — exercised through
`PathologyInterpretationAIPort` exactly as a future consumer module
would call it, per `docs/backend-architecture/12_testing_architecture.md`'s
"Contract tests" framing."""

from uuid import uuid4

from app.modules.pathology_interpretation_ai.application.services.clinical_correlation_service import (  # noqa: E501
    ClinicalCorrelationService,
)
from app.modules.pathology_interpretation_ai.application.services.finding_extraction_service import (  # noqa: E501
    FindingExtractionService,
)
from app.modules.pathology_interpretation_ai.application.services.malignancy_assessment_service import (  # noqa: E501
    MalignancyAssessmentService,
)
from app.modules.pathology_interpretation_ai.application.services.pathology_summary_service import (  # noqa: E501
    PathologySummaryService,
)
from app.modules.pathology_interpretation_ai.application.use_cases.interpret_pathology_report import (  # noqa: E501
    InterpretPathologyReportUseCase,
)
from app.modules.pathology_interpretation_ai.domain.enums import (
    PathologyExaminationType,
    PathologyOutputFormat,
    PathologySetting,
)
from app.modules.pathology_interpretation_ai.public.dto import PathologyInterpretationInput
from app.modules.pathology_interpretation_ai.public.facade import (
    PathologyInterpretationAIFacade,
)
from app.modules.pathology_interpretation_ai.public.interfaces import (
    PathologyInterpretationAIPort,
)
from tests.unit.modules.pathology_interpretation_ai.application.fakes import (
    FakeClinicalCorrelationPort,
    FakeMedicalReasoningAIPort,
    FakePathologyInterpretationAuditLoggerPort,
    FakePathologyInterpretationParserPort,
    FakePathologyInterpretationValidatorPort,
    FakePathologyInterpreterPort,
    make_finding,
    make_result,
)


def _input(**overrides: object) -> PathologyInterpretationInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "report_text": "Sections show benign glandular tissue with reactive changes noted.",
        "examination_type": PathologyExaminationType.HISTOPATHOLOGY,
        "pathology_setting": PathologySetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return PathologyInterpretationInput(**defaults)  # type: ignore[arg-type]


def _facade(
    *,
    generator: FakePathologyInterpreterPort | None = None,
    correlator: FakeClinicalCorrelationPort | None = None,
) -> PathologyInterpretationAIFacade:
    generator = generator or FakePathologyInterpreterPort()
    fake_correlator = correlator or FakeClinicalCorrelationPort()
    finding_extraction_service = FindingExtractionService(correlator=fake_correlator)
    generate_use_case = InterpretPathologyReportUseCase(
        generator=generator,
        parser=FakePathologyInterpretationParserPort(result=make_result()),
        validator=FakePathologyInterpretationValidatorPort(),
        finding_extraction_service=finding_extraction_service,
        malignancy_assessment_service=MalignancyAssessmentService(correlator=fake_correlator),
        correlation_service=ClinicalCorrelationService(),
        medical_reasoning=FakeMedicalReasoningAIPort(),
        audit_logger=FakePathologyInterpretationAuditLoggerPort(),
    )
    return PathologyInterpretationAIFacade(
        generate_use_case=generate_use_case,
        finding_extraction_service=finding_extraction_service,
        summary_service=PathologySummaryService(),
        generator=generator,
    )


class TestPathologyInterpretationAIFacade:
    def test_is_a_pathology_interpretation_ai_port(self) -> None:
        assert isinstance(_facade(), PathologyInterpretationAIPort)

    async def test_generate_interpretation_delegates_to_the_use_case(self) -> None:
        facade = _facade()

        generated = await facade.generate_interpretation(_input())

        assert generated.result is not None
        assert generated.session is not None

    async def test_stream_generate_interpretation_delegates_to_the_generator(self) -> None:
        generator = FakePathologyInterpreterPort(raw_text="hello world")
        facade = _facade(generator=generator)

        chunks = [chunk async for chunk in facade.stream_generate_interpretation(_input())]

        assert "".join(c.delta for c in chunks) == "hello world"

    async def test_render_result_delegates_to_the_summary_service(self) -> None:
        facade = _facade()
        result = make_result()

        rendered = await facade.render_result(result, target_format=PathologyOutputFormat.TEXT)

        assert "PATHOLOGY SUMMARY:" in rendered

    def test_extract_candidate_findings_delegates_to_the_finding_extraction_service(self) -> None:
        candidates = (make_finding(description="Carcinoma"),)
        correlator = FakeClinicalCorrelationPort(candidates=candidates)
        facade = _facade(correlator=correlator)

        result = facade.extract_candidate_findings("some report text")

        assert result == candidates
