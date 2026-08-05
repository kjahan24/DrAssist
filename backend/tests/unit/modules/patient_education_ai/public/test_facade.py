"""Unit tests for `PatientEducationAIFacade` — exercised through
`PatientEducationAIPort` exactly as a future consumer module would call
it, per `docs/backend-architecture/12_testing_architecture.md`'s
"Contract tests" framing."""

from app.modules.patient_education_ai.application.services.discharge_instruction_service import (
    DischargeInstructionService,
)
from app.modules.patient_education_ai.application.services.lifestyle_recommendation_service import (  # noqa: E501
    LifestyleRecommendationService,
)
from app.modules.patient_education_ai.application.services.patient_education_report_renderer import (  # noqa: E501
    PatientEducationReportRenderer,
)
from app.modules.patient_education_ai.application.services.patient_education_service import (
    PatientEducationService,
)
from app.modules.patient_education_ai.application.use_cases.generate_patient_education import (
    GeneratePatientEducationUseCase,
)
from app.modules.patient_education_ai.domain.enums import PatientEducationOutputFormat
from app.modules.patient_education_ai.public.facade import PatientEducationAIFacade
from app.modules.patient_education_ai.public.interfaces import PatientEducationAIPort
from tests.unit.modules.patient_education_ai.application.fakes import (
    FakeDischargeInstructionPort,
    FakeLifestyleRecommendationPort,
    FakeMedicalReasoningAIPort,
    FakePatientEducationAnalysisAuditLoggerPort,
    FakePatientEducationAnalysisGeneratorPort,
    FakePatientEducationAnalysisParserPort,
    FakePatientEducationAnalysisValidatorPort,
    FakePatientEducationPort,
    make_input,
    make_result,
)


def _facade(
    *, generator: FakePatientEducationAnalysisGeneratorPort | None = None
) -> PatientEducationAIFacade:
    generator = generator or FakePatientEducationAnalysisGeneratorPort()
    generate_use_case = GeneratePatientEducationUseCase(
        generator=generator,
        parser=FakePatientEducationAnalysisParserPort(result=make_result()),
        validator=FakePatientEducationAnalysisValidatorPort(),
        patient_education_service=PatientEducationService(
            education_port=FakePatientEducationPort()
        ),
        discharge_instruction_service=DischargeInstructionService(
            discharge_instruction_port=FakeDischargeInstructionPort()
        ),
        lifestyle_recommendation_service=LifestyleRecommendationService(
            lifestyle_recommendation_port=FakeLifestyleRecommendationPort()
        ),
        medical_reasoning=FakeMedicalReasoningAIPort(),
        audit_logger=FakePatientEducationAnalysisAuditLoggerPort(),
    )
    return PatientEducationAIFacade(
        generate_use_case=generate_use_case,
        renderer=PatientEducationReportRenderer(),
        generator=generator,
    )


class TestPatientEducationAIFacade:
    def test_is_a_patient_education_ai_port(self) -> None:
        assert isinstance(_facade(), PatientEducationAIPort)

    async def test_generate_patient_education_delegates_to_the_use_case(self) -> None:
        facade = _facade()

        generated = await facade.generate_patient_education(make_input())

        assert generated.result is not None
        assert generated.session is not None

    async def test_stream_generate_patient_education_delegates_to_the_generator(self) -> None:
        generator = FakePatientEducationAnalysisGeneratorPort(raw_text="hello world")
        facade = _facade(generator=generator)

        chunks = [chunk async for chunk in facade.stream_generate_patient_education(make_input())]

        assert "".join(c.delta for c in chunks) == "hello world"

    async def test_render_result_delegates_to_the_renderer(self) -> None:
        facade = _facade()
        result = make_result()

        rendered = await facade.render_result(
            result, target_format=PatientEducationOutputFormat.TEXT
        )

        assert "PATIENT SUMMARY:" in rendered
