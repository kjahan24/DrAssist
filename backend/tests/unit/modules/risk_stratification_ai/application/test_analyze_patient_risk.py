"""Tests for `AnalyzePatientRiskUseCase` — the full generate/parse/
validate/enrich/audit pipeline, exercised against fakes."""

import pytest

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
from app.modules.risk_stratification_ai.application.services.risk_scoring_service import (
    RiskScoringService,
)
from app.modules.risk_stratification_ai.application.use_cases.analyze_patient_risk import (
    AnalyzePatientRiskUseCase,
)
from app.modules.risk_stratification_ai.domain.enums import OverallRiskLevel, RiskCategory
from app.modules.risk_stratification_ai.domain.exceptions import (
    InvalidRiskScoreError,
    InvalidRiskStratificationResponseFormatError,
)
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
    make_risk_score,
)


def _make_use_case(
    *,
    generator: FakeRiskStratificationAnalysisGeneratorPort | None = None,
    parser: FakeRiskStratificationAnalysisParserPort | None = None,
    validator: FakeRiskStratificationAnalysisValidatorPort | None = None,
    audit_logger: FakeRiskStratificationAnalysisAuditLoggerPort | None = None,
    medical_reasoning: FakeMedicalReasoningAIPort | None = None,
    scoring_port: FakeRiskScoringPort | None = None,
    clinical_risk_port: FakeClinicalRiskPort | None = None,
    early_warning_port: FakeEarlyWarningPort | None = None,
) -> tuple[AnalyzePatientRiskUseCase, dict[str, object]]:
    generator = generator or FakeRiskStratificationAnalysisGeneratorPort()
    parser = parser or FakeRiskStratificationAnalysisParserPort()
    validator = validator or FakeRiskStratificationAnalysisValidatorPort()
    audit_logger = audit_logger or FakeRiskStratificationAnalysisAuditLoggerPort()
    medical_reasoning = medical_reasoning or FakeMedicalReasoningAIPort()
    scoring_port = scoring_port or FakeRiskScoringPort()
    clinical_risk_port = clinical_risk_port or FakeClinicalRiskPort()
    early_warning_port = early_warning_port or FakeEarlyWarningPort()

    use_case = AnalyzePatientRiskUseCase(
        generator=generator,
        parser=parser,
        validator=validator,
        risk_scoring_service=RiskScoringService(scoring_port=scoring_port),
        clinical_risk_assessment_service=ClinicalRiskAssessmentService(
            clinical_risk_port=clinical_risk_port
        ),
        early_warning_service=EarlyWarningService(early_warning_port=early_warning_port),
        risk_explanation_service=RiskExplanationService(),
        monitoring_recommendation_service=MonitoringRecommendationService(
            early_warning_port=early_warning_port
        ),
        medical_reasoning=medical_reasoning,
        audit_logger=audit_logger,
    )
    doubles: dict[str, object] = {
        "generator": generator,
        "parser": parser,
        "validator": validator,
        "audit_logger": audit_logger,
        "medical_reasoning": medical_reasoning,
        "scoring_port": scoring_port,
        "clinical_risk_port": clinical_risk_port,
        "early_warning_port": early_warning_port,
    }
    return use_case, doubles


class TestSuccessfulExecution:
    async def test_returns_generated_result_with_session(self) -> None:
        use_case, doubles = _make_use_case()
        generated = await use_case.execute(make_input())

        generator = doubles["generator"]
        assert isinstance(generator, FakeRiskStratificationAnalysisGeneratorPort)
        assert generated.session is generator._session

    async def test_logs_generation_on_success(self) -> None:
        use_case, doubles = _make_use_case()
        await use_case.execute(make_input())

        audit_logger = doubles["audit_logger"]
        assert isinstance(audit_logger, FakeRiskStratificationAnalysisAuditLoggerPort)
        assert len(audit_logger.sessions) == 1
        assert audit_logger.failures == []

    async def test_parser_and_validator_receive_the_generated_text(self) -> None:
        use_case, doubles = _make_use_case(
            generator=FakeRiskStratificationAnalysisGeneratorPort(raw_text="raw-ai-output")
        )
        await use_case.execute(make_input())

        parser = doubles["parser"]
        assert isinstance(parser, FakeRiskStratificationAnalysisParserPort)
        assert parser.received[0][0] == "raw-ai-output"


class TestFailureHandling:
    async def test_parser_error_is_logged_and_reraised(self) -> None:
        error = InvalidRiskStratificationResponseFormatError("no JSON object found")
        use_case, doubles = _make_use_case(
            parser=FakeRiskStratificationAnalysisParserPort(error=error)
        )

        with pytest.raises(InvalidRiskStratificationResponseFormatError):
            await use_case.execute(make_input())

        audit_logger = doubles["audit_logger"]
        assert isinstance(audit_logger, FakeRiskStratificationAnalysisAuditLoggerPort)
        assert len(audit_logger.failures) == 1
        assert audit_logger.failures[0]["stage"] == "parse_or_validate"
        assert (
            audit_logger.failures[0]["error_code"] == "InvalidRiskStratificationResponseFormatError"
        )

    async def test_validator_error_is_logged_and_reraised(self) -> None:
        error = InvalidRiskScoreError("news2", 99.0)
        use_case, doubles = _make_use_case(
            validator=FakeRiskStratificationAnalysisValidatorPort(error=error)
        )

        with pytest.raises(InvalidRiskScoreError):
            await use_case.execute(make_input())

        audit_logger = doubles["audit_logger"]
        assert isinstance(audit_logger, FakeRiskStratificationAnalysisAuditLoggerPort)
        assert len(audit_logger.failures) == 1

    async def test_non_domain_generator_errors_propagate_unaudited(self) -> None:
        use_case, doubles = _make_use_case(
            generator=FakeRiskStratificationAnalysisGeneratorPort(error=RuntimeError("timeout"))
        )

        with pytest.raises(RuntimeError):
            await use_case.execute(make_input())

        audit_logger = doubles["audit_logger"]
        assert isinstance(audit_logger, FakeRiskStratificationAnalysisAuditLoggerPort)
        assert audit_logger.failures == []
        assert audit_logger.sessions == []


class TestEnrichment:
    async def test_merges_deterministic_standardized_scores(self) -> None:
        news2 = make_risk_score(category=RiskCategory.NEWS2, score_value=3.0)
        use_case, _ = _make_use_case(
            parser=FakeRiskStratificationAnalysisParserPort(result=make_result(risk_scores=())),
            scoring_port=FakeRiskScoringPort(news2=news2),
        )

        generated = await use_case.execute(make_input())

        assert news2 in generated.result.risk_scores

    async def test_merges_deterministic_qualitative_scores(self) -> None:
        sepsis_score = make_risk_score(category=RiskCategory.SEPSIS_RISK, score_value=None)
        use_case, _ = _make_use_case(
            parser=FakeRiskStratificationAnalysisParserPort(result=make_result(risk_scores=())),
            clinical_risk_port=FakeClinicalRiskPort(score=sepsis_score),
        )

        generated = await use_case.execute(make_input())

        categories = {score.category for score in generated.result.risk_scores}
        assert RiskCategory.SEPSIS_RISK in categories

    async def test_applies_deterministic_floor_to_overall_risk_level(self) -> None:
        critical_news2 = make_risk_score(category=RiskCategory.NEWS2, score_value=9.0)
        use_case, _ = _make_use_case(
            parser=FakeRiskStratificationAnalysisParserPort(
                result=make_result(overall_risk_level=OverallRiskLevel.LOW, risk_scores=())
            ),
            scoring_port=FakeRiskScoringPort(news2=critical_news2),
        )

        generated = await use_case.execute(make_input())

        assert generated.result.overall_risk_level is OverallRiskLevel.CRITICAL

    async def test_merges_early_warning_indicators(self) -> None:
        use_case, _ = _make_use_case(
            early_warning_port=FakeEarlyWarningPort(triggers=("SpO2 88% (low)",))
        )

        generated = await use_case.execute(make_input())

        assert "SpO2 88% (low)" in generated.result.early_warning_indicators

    async def test_merges_red_flag_alerts(self) -> None:
        use_case, _ = _make_use_case(
            early_warning_port=FakeEarlyWarningPort(triggers=("HR 145/min",))
        )

        generated = await use_case.execute(make_input())

        assert "HR 145/min" in generated.result.red_flag_alerts

    async def test_falls_back_to_synthesized_clinical_reasoning_when_ai_blank(self) -> None:
        score = make_risk_score(clinical_explanation="NEWS2 score of 7.")
        use_case, _ = _make_use_case(
            parser=FakeRiskStratificationAnalysisParserPort(
                result=make_result(clinical_reasoning="", risk_scores=(score,))
            ),
        )

        generated = await use_case.execute(make_input())

        assert generated.result.clinical_reasoning == "NEWS2 score of 7."

    async def test_confidence_score_delegates_to_medical_reasoning_port(self) -> None:
        medical_reasoning = FakeMedicalReasoningAIPort(confidence_value=0.42)
        use_case, _ = _make_use_case(
            parser=FakeRiskStratificationAnalysisParserPort(
                result=make_result(confidence_score=None)
            ),
            medical_reasoning=medical_reasoning,
        )

        generated = await use_case.execute(make_input())

        assert generated.result.confidence_score == 0.42
        assert len(medical_reasoning.score_confidence_calls) == 1

    async def test_confidence_score_uses_ai_reported_value_when_present(self) -> None:
        use_case, _ = _make_use_case(
            parser=FakeRiskStratificationAnalysisParserPort(
                result=make_result(confidence_score=0.9)
            ),
        )

        generated = await use_case.execute(make_input())

        assert generated.result.confidence_score == 0.9
