"""Unit tests for `LabInterpretationAIFacade` — exercised through
`LabInterpretationAIPort` exactly as a future consumer module would call
it, per `docs/backend-architecture/12_testing_architecture.md`'s
"Contract tests" framing."""

from uuid import uuid4

from app.modules.lab_interpretation_ai.application.services.critical_value_detection_service import (  # noqa: E501
    CriticalValueDetectionService,
)
from app.modules.lab_interpretation_ai.application.services.lab_interpretation_renderer import (
    LabInterpretationRenderer,
)
from app.modules.lab_interpretation_ai.application.services.lab_recommendation_service import (
    LabRecommendationService,
)
from app.modules.lab_interpretation_ai.application.services.lab_trend_analysis_service import (
    LabTrendAnalysisService,
)
from app.modules.lab_interpretation_ai.application.use_cases.interpret_lab_results import (
    InterpretLabResultsUseCase,
)
from app.modules.lab_interpretation_ai.domain.enums import (
    LabInterpretationOutputFormat,
    LabInterpretationSetting,
)
from app.modules.lab_interpretation_ai.public.dto import LabInterpretationInput
from app.modules.lab_interpretation_ai.public.facade import LabInterpretationAIFacade
from app.modules.lab_interpretation_ai.public.interfaces import LabInterpretationAIPort
from tests.unit.modules.lab_interpretation_ai.application.fakes import (
    FakeCriticalValueAnalyzerPort,
    FakeLabInterpretationAuditLoggerPort,
    FakeLabInterpretationParserPort,
    FakeLabInterpretationValidatorPort,
    FakeLabInterpreterPort,
    FakeMedicalReasoningAIPort,
    make_lab_value,
    make_result,
)


def _input(**overrides: object) -> LabInterpretationInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "lab_values": (make_lab_value(),),
        "lab_setting": LabInterpretationSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return LabInterpretationInput(**defaults)  # type: ignore[arg-type]


def _facade(*, generator: FakeLabInterpreterPort | None = None) -> LabInterpretationAIFacade:
    generator = generator or FakeLabInterpreterPort()
    generate_use_case = InterpretLabResultsUseCase(
        generator=generator,
        parser=FakeLabInterpretationParserPort(result=make_result()),
        validator=FakeLabInterpretationValidatorPort(),
        critical_value_service=CriticalValueDetectionService(
            analyzer=FakeCriticalValueAnalyzerPort()
        ),
        trend_service=LabTrendAnalysisService(),
        recommendation_service=LabRecommendationService(),
        medical_reasoning=FakeMedicalReasoningAIPort(),
        audit_logger=FakeLabInterpretationAuditLoggerPort(),
    )
    return LabInterpretationAIFacade(
        generate_use_case=generate_use_case,
        renderer=LabInterpretationRenderer(),
        generator=generator,
    )


class TestLabInterpretationAIFacade:
    def test_is_a_lab_interpretation_ai_port(self) -> None:
        assert isinstance(_facade(), LabInterpretationAIPort)

    async def test_generate_interpretation_delegates_to_the_use_case(self) -> None:
        facade = _facade()

        generated = await facade.generate_interpretation(_input())

        assert generated.result is not None
        assert generated.session is not None

    async def test_stream_generate_interpretation_delegates_to_the_generator(self) -> None:
        generator = FakeLabInterpreterPort(raw_text="hello world")
        facade = _facade(generator=generator)

        chunks = [chunk async for chunk in facade.stream_generate_interpretation(_input())]

        assert "".join(c.delta for c in chunks) == "hello world"

    async def test_render_result_delegates_to_the_renderer(self) -> None:
        facade = _facade()
        result = make_result()

        rendered = await facade.render_result(
            result, target_format=LabInterpretationOutputFormat.TEXT
        )

        assert "OVERALL INTERPRETATION:" in rendered
