"""Unit tests for `InterpretRadiologyReportUseCase`."""

from uuid import uuid4

import pytest

from app.modules.radiology_interpretation_ai.application.services.critical_finding_detection_service import (  # noqa: E501
    CriticalFindingDetectionService,
)
from app.modules.radiology_interpretation_ai.application.services.finding_extraction_service import (  # noqa: E501
    FindingExtractionService,
)
from app.modules.radiology_interpretation_ai.application.services.follow_up_recommendation_service import (  # noqa: E501
    FollowUpRecommendationService,
)
from app.modules.radiology_interpretation_ai.application.use_cases.interpret_radiology_report import (  # noqa: E501
    InterpretRadiologyReportUseCase,
)
from app.modules.radiology_interpretation_ai.domain.enums import (
    RadiologyExaminationType,
    RadiologyFindingCategory,
    RadiologyOutputFormat,
    RadiologySetting,
)
from app.modules.radiology_interpretation_ai.domain.exceptions import (
    DuplicateRadiologyFindingError,
    HallucinatedRadiologyFindingError,
    InconsistentRadiologyRecommendationsError,
    InvalidRadiologyConfidenceValueError,
    InvalidRadiologyInterpretationResponseFormatError,
)
from app.modules.radiology_interpretation_ai.domain.value_objects import (
    RadiologyInterpretationInput,
)
from tests.unit.modules.radiology_interpretation_ai.application.fakes import (
    FakeFindingExtractionPort,
    FakeMedicalReasoningAIPort,
    FakeRadiologyInterpretationAuditLoggerPort,
    FakeRadiologyInterpretationParserPort,
    FakeRadiologyInterpretationValidatorPort,
    FakeRadiologyInterpreterPort,
    make_finding,
    make_generation_session,
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


def _use_case(
    *,
    generator: FakeRadiologyInterpreterPort | None = None,
    parser: FakeRadiologyInterpretationParserPort | None = None,
    validator: FakeRadiologyInterpretationValidatorPort | None = None,
    audit_logger: FakeRadiologyInterpretationAuditLoggerPort | None = None,
    finding_extractor: FakeFindingExtractionPort | None = None,
    medical_reasoning: FakeMedicalReasoningAIPort | None = None,
) -> tuple[
    InterpretRadiologyReportUseCase,
    FakeRadiologyInterpreterPort,
    FakeRadiologyInterpretationParserPort,
    FakeRadiologyInterpretationValidatorPort,
    FakeRadiologyInterpretationAuditLoggerPort,
    FakeMedicalReasoningAIPort,
]:
    generator = generator or FakeRadiologyInterpreterPort()
    parser = parser or FakeRadiologyInterpretationParserPort()
    validator = validator or FakeRadiologyInterpretationValidatorPort()
    audit_logger = audit_logger or FakeRadiologyInterpretationAuditLoggerPort()
    medical_reasoning = medical_reasoning or FakeMedicalReasoningAIPort()
    extractor = finding_extractor or FakeFindingExtractionPort()
    use_case = InterpretRadiologyReportUseCase(
        generator=generator,
        parser=parser,
        validator=validator,
        finding_extraction_service=FindingExtractionService(extractor=extractor),
        critical_finding_service=CriticalFindingDetectionService(extractor=extractor),
        recommendation_service=FollowUpRecommendationService(),
        medical_reasoning=medical_reasoning,
        audit_logger=audit_logger,
    )
    return use_case, generator, parser, validator, audit_logger, medical_reasoning


class TestInterpretRadiologyReportUseCaseHappyPath:
    async def test_returns_result_and_session(self) -> None:
        use_case, *_ = _use_case()

        generated = await use_case.execute(_input())

        assert generated.result is not None
        assert generated.session is not None

    async def test_calls_generator_then_parser_then_validator_in_order(self) -> None:
        parsed_result = make_result()
        use_case, generator, parser, validator, _audit, _reasoning = _use_case(
            parser=FakeRadiologyInterpretationParserPort(result=parsed_result)
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

        await use_case.execute(_input(output_format=RadiologyOutputFormat.MARKDOWN))

        assert parser.received[0][1] is RadiologyOutputFormat.MARKDOWN

    async def test_escalates_findings_via_the_finding_extractor(self) -> None:
        parsed_result = make_result(
            findings=(make_finding(category=RadiologyFindingCategory.ABNORMAL),)
        )
        extractor = FakeFindingExtractionPort(classification=RadiologyFindingCategory.CRITICAL)
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeRadiologyInterpretationParserPort(result=parsed_result),
            finding_extractor=extractor,
        )

        generated = await use_case.execute(_input())

        assert generated.result.findings[0].category is RadiologyFindingCategory.CRITICAL

    async def test_merges_findings_missed_by_the_ai(self) -> None:
        parsed_result = make_result(
            findings=(
                make_finding(description="Clear lungs", category=RadiologyFindingCategory.NORMAL),
            )
        )
        missed_candidate = make_finding(
            description="Pneumothorax", category=RadiologyFindingCategory.CRITICAL
        )
        extractor = FakeFindingExtractionPort(candidates=(missed_candidate,))
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeRadiologyInterpretationParserPort(result=parsed_result),
            finding_extractor=extractor,
        )

        generated = await use_case.execute(_input())

        descriptions = {f.description for f in generated.result.findings}
        assert "Pneumothorax" in descriptions
        assert "Clear lungs" in descriptions

    async def test_derives_and_merges_follow_up_and_referral_for_critical_findings(self) -> None:
        parsed_result = make_result(
            findings=(
                make_finding(
                    description="Large pneumothorax", category=RadiologyFindingCategory.CRITICAL
                ),
            ),
            suggested_follow_up_imaging=("Existing follow-up",),
        )
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeRadiologyInterpretationParserPort(result=parsed_result)
        )

        generated = await use_case.execute(_input())

        assert "Existing follow-up" in generated.result.suggested_follow_up_imaging
        assert (
            "Further imaging correlation recommended for: Large pneumothorax"
            in generated.result.suggested_follow_up_imaging
        )
        assert (
            "Urgent specialist referral recommended given critical finding: Large pneumothorax"
            in generated.result.suggested_specialist_referral
        )

    async def test_deduplicates_recommendation_lists(self) -> None:
        parsed_result = make_result(
            differential_imaging_considerations=("Possible mass", "possible mass")
        )
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeRadiologyInterpretationParserPort(result=parsed_result)
        )

        generated = await use_case.execute(_input())

        assert len(generated.result.differential_imaging_considerations) == 1

    async def test_scores_confidence_via_the_medical_reasoning_facade(self) -> None:
        parsed_result = make_result(
            confidence_score=None,
            findings=(make_finding(), make_finding(description="Second finding")),
        )
        reasoning = FakeMedicalReasoningAIPort(confidence_value=0.61)
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeRadiologyInterpretationParserPort(result=parsed_result),
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
            parser=FakeRadiologyInterpretationParserPort(result=parsed_result)
        )

        generated = await use_case.execute(_input())

        assert generated.result.confidence_score == 0.92


class TestInterpretRadiologyReportUseCaseFailureModes:
    async def test_parsing_failure_raises_and_logs_a_failure(self) -> None:
        parser = FakeRadiologyInterpretationParserPort(
            error=InvalidRadiologyInterpretationResponseFormatError("malformed JSON")
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(parser=parser)

        with pytest.raises(InvalidRadiologyInterpretationResponseFormatError):
            await use_case.execute(_input())

        assert audit.failures[0]["stage"] == "parse_or_validate"
        assert (
            audit.failures[0]["error_code"] == "InvalidRadiologyInterpretationResponseFormatError"
        )
        assert audit.sessions == []

    async def test_duplicate_finding_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeRadiologyInterpretationValidatorPort(
            error=DuplicateRadiologyFindingError("Pneumothorax")
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            validator=validator
        )

        with pytest.raises(DuplicateRadiologyFindingError):
            await use_case.execute(_input())

        assert audit.failures[0]["error_code"] == "DuplicateRadiologyFindingError"

    async def test_hallucinated_finding_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeRadiologyInterpretationValidatorPort(
            error=HallucinatedRadiologyFindingError("examination_summary", "[insert]")
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            validator=validator
        )

        with pytest.raises(HallucinatedRadiologyFindingError):
            await use_case.execute(_input())

        assert audit.failures[0]["error_code"] == "HallucinatedRadiologyFindingError"

    async def test_inconsistent_recommendations_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeRadiologyInterpretationValidatorPort(
            error=InconsistentRadiologyRecommendationsError(
                "suggested_follow_up_imaging", "Repeat CT"
            )
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            validator=validator
        )

        with pytest.raises(InconsistentRadiologyRecommendationsError):
            await use_case.execute(_input())

        assert audit.failures[0]["error_code"] == "InconsistentRadiologyRecommendationsError"

    async def test_invalid_confidence_value_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeRadiologyInterpretationValidatorPort(
            error=InvalidRadiologyConfidenceValueError()
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            validator=validator
        )

        with pytest.raises(InvalidRadiologyConfidenceValueError):
            await use_case.execute(_input())

        assert audit.failures[0]["error_code"] == "InvalidRadiologyConfidenceValueError"

    async def test_ai_foundation_errors_from_the_generator_propagate_unwrapped(self) -> None:
        class _FakeFoundationError(Exception):
            pass

        generator = FakeRadiologyInterpreterPort(error=_FakeFoundationError("provider down"))
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
        generator = FakeRadiologyInterpreterPort(session=session)
        parser = FakeRadiologyInterpretationParserPort(
            error=InvalidRadiologyInterpretationResponseFormatError("x")
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            generator=generator, parser=parser
        )

        with pytest.raises(InvalidRadiologyInterpretationResponseFormatError):
            await use_case.execute(_input())

        assert audit.failures[0]["generation_id"] == session.generation_id
