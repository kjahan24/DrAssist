"""Unit tests for `RiskStratificationAIFacade` — exercised through
`RiskStratificationAIPort` exactly as a future consumer module would
call it, per `docs/backend-architecture/12_testing_architecture.md`'s
"Contract tests" framing."""

from app.modules.risk_stratification_ai.application.services.clinical_risk_assessment_service import (  # noqa: E501
    ClinicalRiskAssessmentService,
)
from app.modules.risk_stratification_ai.application.services.early_warning_service import (
    EarlyWarningService,
)
from app.modules.risk_stratification_ai.application.services.monitoring_recommendation_service import (  # noqa: E501
    MonitoringRecommendationService,
)
from app.modules.risk_stratification_ai.application.services.risk_explanation_service import (
    RiskExplanationService,
)
from app.modules.risk_stratification_ai.application.services.risk_report_renderer import (
    RiskReportRenderer,
)
from app.modules.risk_stratification_ai.application.services.risk_scoring_service import (
    RiskScoringService,
)
from app.modules.risk_stratification_ai.application.use_cases.analyze_patient_risk import (
    AnalyzePatientRiskUseCase,
)
from app.modules.risk_stratification_ai.domain.enums import RiskStratificationOutputFormat
from app.modules.risk_stratification_ai.public.facade import RiskStratificationAIFacade
from app.modules.risk_stratification_ai.public.interfaces import RiskStratificationAIPort
from tests.unit.modules.risk_stratification_ai.application.fakes import (
    FakeClinicalRiskPort,
    FakeEarlyWarningPort,
    FakeMedicalReasoningAIPort,
    FakeRiskScoringPort,
    FakeRiskStratificationAnalysisAuditLoggerPort,
    FakeRiskStratificationAnalysisGeneratorPort,
    FakeRiskStratificationAnalysisParserPort,
    FakeRiskStratificationAnalysisValidatorPort,
    make_input,
    make_result,
)


def _facade(
    *, generator: FakeRiskStratificationAnalysisGeneratorPort | None = None
) -> RiskStratificationAIFacade:
    generator = generator or FakeRiskStratificationAnalysisGeneratorPort()
    early_warning_port = FakeEarlyWarningPort()
    analyze_use_case = AnalyzePatientRiskUseCase(
        generator=generator,
        parser=FakeRiskStratificationAnalysisParserPort(result=make_result()),
        validator=FakeRiskStratificationAnalysisValidatorPort(),
        risk_scoring_service=RiskScoringService(scoring_port=FakeRiskScoringPort()),
        clinical_risk_assessment_service=ClinicalRiskAssessmentService(
            clinical_risk_port=FakeClinicalRiskPort()
        ),
        early_warning_service=EarlyWarningService(early_warning_port=early_warning_port),
        risk_explanation_service=RiskExplanationService(),
        monitoring_recommendation_service=MonitoringRecommendationService(
            early_warning_port=early_warning_port
        ),
        medical_reasoning=FakeMedicalReasoningAIPort(),
        audit_logger=FakeRiskStratificationAnalysisAuditLoggerPort(),
    )
    return RiskStratificationAIFacade(
        analyze_use_case=analyze_use_case,
        renderer=RiskReportRenderer(),
        generator=generator,
    )


class TestRiskStratificationAIFacade:
    def test_is_a_risk_stratification_ai_port(self) -> None:
        assert isinstance(_facade(), RiskStratificationAIPort)

    async def test_analyze_patient_risk_delegates_to_the_use_case(self) -> None:
        facade = _facade()

        generated = await facade.analyze_patient_risk(make_input())

        assert generated.result is not None
        assert generated.session is not None

    async def test_stream_analyze_patient_risk_delegates_to_the_generator(self) -> None:
        generator = FakeRiskStratificationAnalysisGeneratorPort(raw_text="hello world")
        facade = _facade(generator=generator)

        chunks = [chunk async for chunk in facade.stream_analyze_patient_risk(make_input())]

        assert "".join(c.delta for c in chunks) == "hello world"

    async def test_render_result_delegates_to_the_renderer(self) -> None:
        facade = _facade()
        result = make_result()

        rendered = await facade.render_result(
            result, target_format=RiskStratificationOutputFormat.TEXT
        )

        assert "OVERALL RISK LEVEL:" in rendered
