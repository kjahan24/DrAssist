"""Unit tests for `InterpretLabResultsUseCase`."""

from uuid import uuid4

import pytest

from app.modules.lab_interpretation_ai.application.services.critical_value_detection_service import (  # noqa: E501
    CriticalValueDetectionService,
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
    LabFindingFlag,
    LabInterpretationOutputFormat,
    LabInterpretationSetting,
)
from app.modules.lab_interpretation_ai.domain.exceptions import (
    HallucinatedLabValueError,
    InvalidLabInterpretationResponseFormatError,
    MissingLabReasoningError,
)
from app.modules.lab_interpretation_ai.domain.value_objects import LabInterpretationInput
from tests.unit.modules.lab_interpretation_ai.application.fakes import (
    FakeCriticalValueAnalyzerPort,
    FakeLabInterpretationAuditLoggerPort,
    FakeLabInterpretationParserPort,
    FakeLabInterpretationValidatorPort,
    FakeLabInterpreterPort,
    FakeMedicalReasoningAIPort,
    make_finding,
    make_generation_session,
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


def _use_case(
    *,
    generator: FakeLabInterpreterPort | None = None,
    parser: FakeLabInterpretationParserPort | None = None,
    validator: FakeLabInterpretationValidatorPort | None = None,
    audit_logger: FakeLabInterpretationAuditLoggerPort | None = None,
    critical_value_analyzer: FakeCriticalValueAnalyzerPort | None = None,
    medical_reasoning: FakeMedicalReasoningAIPort | None = None,
) -> tuple[
    InterpretLabResultsUseCase,
    FakeLabInterpreterPort,
    FakeLabInterpretationParserPort,
    FakeLabInterpretationValidatorPort,
    FakeLabInterpretationAuditLoggerPort,
    FakeMedicalReasoningAIPort,
]:
    generator = generator or FakeLabInterpreterPort()
    parser = parser or FakeLabInterpretationParserPort()
    validator = validator or FakeLabInterpretationValidatorPort()
    audit_logger = audit_logger or FakeLabInterpretationAuditLoggerPort()
    medical_reasoning = medical_reasoning or FakeMedicalReasoningAIPort()
    use_case = InterpretLabResultsUseCase(
        generator=generator,
        parser=parser,
        validator=validator,
        critical_value_service=CriticalValueDetectionService(
            analyzer=critical_value_analyzer or FakeCriticalValueAnalyzerPort()
        ),
        trend_service=LabTrendAnalysisService(),
        recommendation_service=LabRecommendationService(),
        medical_reasoning=medical_reasoning,
        audit_logger=audit_logger,
    )
    return use_case, generator, parser, validator, audit_logger, medical_reasoning


class TestInterpretLabResultsUseCaseHappyPath:
    async def test_returns_result_and_session(self) -> None:
        use_case, *_ = _use_case()

        generated = await use_case.execute(_input())

        assert generated.result is not None
        assert generated.session is not None

    async def test_calls_generator_then_parser_then_validator_in_order(self) -> None:
        parsed_result = make_result()
        use_case, generator, parser, validator, _audit, _reasoning = _use_case(
            parser=FakeLabInterpretationParserPort(result=parsed_result)
        )
        input_dto = _input()

        await use_case.execute(input_dto)

        assert generator.received == [input_dto]
        assert parser.received[0][0] == generator._raw_text
        assert validator.received == [parsed_result]

    async def test_logs_a_generation_session_on_success(self) -> None:
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case()

        await use_case.execute(_input())

        assert len(audit.sessions) == 1
        assert audit.failures == []

    async def test_passes_output_format_through_to_the_parser(self) -> None:
        use_case, _generator, parser, _validator, _audit, _reasoning = _use_case()

        await use_case.execute(_input(output_format=LabInterpretationOutputFormat.MARKDOWN))

        assert parser.received[0][1] is LabInterpretationOutputFormat.MARKDOWN

    async def test_reconciles_findings_via_the_critical_value_analyzer(self) -> None:
        parsed_result = make_result(findings=(make_finding(flag=LabFindingFlag.ABNORMAL_HIGH),))
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeLabInterpretationParserPort(result=parsed_result),
            critical_value_analyzer=FakeCriticalValueAnalyzerPort(
                classification=LabFindingFlag.CRITICAL_HIGH
            ),
        )

        generated = await use_case.execute(_input())

        assert generated.result.findings[0].flag is LabFindingFlag.CRITICAL_HIGH

    async def test_merges_trend_descriptions_into_supporting_evidence(self) -> None:
        parsed_result = make_result(supporting_evidence=("AI-reported evidence",))
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeLabInterpretationParserPort(result=parsed_result)
        )
        input_dto = _input(
            lab_values=(
                make_lab_value(value="4.0", numeric_value=4.0),
                make_lab_value(value="5.5", numeric_value=5.5),
            )
        )

        generated = await use_case.execute(input_dto)

        assert "AI-reported evidence" in generated.result.supporting_evidence
        assert any("rising" in item for item in generated.result.supporting_evidence)

    async def test_derives_and_merges_follow_up_tests_for_critical_findings(self) -> None:
        parsed_result = make_result(
            findings=(make_finding(test_name="Potassium", flag=LabFindingFlag.CRITICAL_HIGH),),
            suggested_follow_up_tests=("Existing follow-up",),
        )
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeLabInterpretationParserPort(result=parsed_result)
        )

        generated = await use_case.execute(_input())

        assert "Existing follow-up" in generated.result.suggested_follow_up_tests
        assert "Repeat Potassium to confirm critical result" in (
            generated.result.suggested_follow_up_tests
        )

    async def test_deduplicates_recommendation_lists(self) -> None:
        parsed_result = make_result(monitoring_recommendations=("Recheck in 24h", "recheck in 24h"))
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeLabInterpretationParserPort(result=parsed_result)
        )

        generated = await use_case.execute(_input())

        assert len(generated.result.monitoring_recommendations) == 1

    async def test_scores_confidence_via_the_medical_reasoning_facade(self) -> None:
        parsed_result = make_result(
            confidence_score=None, supporting_evidence=("Evidence A", "Evidence B")
        )
        reasoning = FakeMedicalReasoningAIPort(confidence_value=0.61)
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeLabInterpretationParserPort(result=parsed_result),
            medical_reasoning=reasoning,
        )

        generated = await use_case.execute(_input())

        assert generated.result.confidence_score == 0.61
        call = reasoning.score_confidence_calls[0]
        assert call["ai_reported"] is None
        assert call["supporting_count"] == 2
        assert call["contradicting_count"] == 0
        assert call["missing_information_count"] == 0

    async def test_preserves_ai_reported_confidence(self) -> None:
        parsed_result = make_result(confidence_score=0.92)
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeLabInterpretationParserPort(result=parsed_result)
        )

        generated = await use_case.execute(_input())

        assert generated.result.confidence_score == 0.92


class TestInterpretLabResultsUseCaseFailureModes:
    async def test_parsing_failure_raises_and_logs_a_failure(self) -> None:
        parser = FakeLabInterpretationParserPort(
            error=InvalidLabInterpretationResponseFormatError("malformed JSON")
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(parser=parser)

        with pytest.raises(InvalidLabInterpretationResponseFormatError):
            await use_case.execute(_input())

        assert audit.failures[0]["stage"] == "parse_or_validate"
        assert audit.failures[0]["error_code"] == "InvalidLabInterpretationResponseFormatError"
        assert audit.sessions == []

    async def test_missing_reasoning_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeLabInterpretationValidatorPort(
            error=MissingLabReasoningError("overall_interpretation must not be blank")
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            validator=validator
        )

        with pytest.raises(MissingLabReasoningError):
            await use_case.execute(_input())

        assert audit.failures[0]["error_code"] == "MissingLabReasoningError"

    async def test_hallucinated_value_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeLabInterpretationValidatorPort(
            error=HallucinatedLabValueError("overall_interpretation", "[insert]")
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            validator=validator
        )

        with pytest.raises(HallucinatedLabValueError):
            await use_case.execute(_input())

        assert audit.failures[0]["error_code"] == "HallucinatedLabValueError"

    async def test_ai_foundation_errors_from_the_generator_propagate_unwrapped(self) -> None:
        class _FakeFoundationError(Exception):
            pass

        generator = FakeLabInterpreterPort(error=_FakeFoundationError("provider down"))
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            generator=generator
        )

        with pytest.raises(_FakeFoundationError):
            await use_case.execute(_input())

        assert audit.failures == []
        assert audit.sessions == []

    async def test_generation_id_on_failure_log_matches_the_session_from_the_generator(
        self,
    ) -> None:
        session = make_generation_session()
        generator = FakeLabInterpreterPort(session=session)
        parser = FakeLabInterpretationParserPort(
            error=InvalidLabInterpretationResponseFormatError("x")
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            generator=generator, parser=parser
        )

        with pytest.raises(InvalidLabInterpretationResponseFormatError):
            await use_case.execute(_input())

        assert audit.failures[0]["generation_id"] == session.generation_id
