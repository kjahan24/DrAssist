"""Unit tests for `InterpretPathologyReportUseCase`."""

from uuid import uuid4

import pytest

from app.modules.pathology_interpretation_ai.application.services.clinical_correlation_service import (  # noqa: E501
    ClinicalCorrelationService,
)
from app.modules.pathology_interpretation_ai.application.services.finding_extraction_service import (  # noqa: E501
    FindingExtractionService,
)
from app.modules.pathology_interpretation_ai.application.services.malignancy_assessment_service import (  # noqa: E501
    MalignancyAssessmentService,
)
from app.modules.pathology_interpretation_ai.application.use_cases.interpret_pathology_report import (  # noqa: E501
    InterpretPathologyReportUseCase,
)
from app.modules.pathology_interpretation_ai.domain.enums import (
    PathologyExaminationType,
    PathologyFindingCategory,
    PathologyOutputFormat,
    PathologySetting,
)
from app.modules.pathology_interpretation_ai.domain.exceptions import (
    DuplicatePathologyFindingError,
    HallucinatedPathologyFindingError,
    InconsistentPathologyConclusionsError,
    InvalidPathologyConfidenceValueError,
    InvalidPathologyInterpretationResponseFormatError,
)
from app.modules.pathology_interpretation_ai.domain.value_objects import (
    PathologyInterpretationInput,
)
from tests.unit.modules.pathology_interpretation_ai.application.fakes import (
    FakeClinicalCorrelationPort,
    FakeMedicalReasoningAIPort,
    FakePathologyInterpretationAuditLoggerPort,
    FakePathologyInterpretationParserPort,
    FakePathologyInterpretationValidatorPort,
    FakePathologyInterpreterPort,
    make_finding,
    make_generation_session,
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


def _use_case(
    *,
    generator: FakePathologyInterpreterPort | None = None,
    parser: FakePathologyInterpretationParserPort | None = None,
    validator: FakePathologyInterpretationValidatorPort | None = None,
    audit_logger: FakePathologyInterpretationAuditLoggerPort | None = None,
    correlator: FakeClinicalCorrelationPort | None = None,
    medical_reasoning: FakeMedicalReasoningAIPort | None = None,
) -> tuple[
    InterpretPathologyReportUseCase,
    FakePathologyInterpreterPort,
    FakePathologyInterpretationParserPort,
    FakePathologyInterpretationValidatorPort,
    FakePathologyInterpretationAuditLoggerPort,
    FakeMedicalReasoningAIPort,
]:
    generator = generator or FakePathologyInterpreterPort()
    parser = parser or FakePathologyInterpretationParserPort()
    validator = validator or FakePathologyInterpretationValidatorPort()
    audit_logger = audit_logger or FakePathologyInterpretationAuditLoggerPort()
    medical_reasoning = medical_reasoning or FakeMedicalReasoningAIPort()
    fake_correlator = correlator or FakeClinicalCorrelationPort()
    use_case = InterpretPathologyReportUseCase(
        generator=generator,
        parser=parser,
        validator=validator,
        finding_extraction_service=FindingExtractionService(correlator=fake_correlator),
        malignancy_assessment_service=MalignancyAssessmentService(correlator=fake_correlator),
        correlation_service=ClinicalCorrelationService(),
        medical_reasoning=medical_reasoning,
        audit_logger=audit_logger,
    )
    return use_case, generator, parser, validator, audit_logger, medical_reasoning


class TestInterpretPathologyReportUseCaseHappyPath:
    async def test_returns_result_and_session(self) -> None:
        use_case, *_ = _use_case()

        generated = await use_case.execute(_input())

        assert generated.result is not None
        assert generated.session is not None

    async def test_calls_generator_then_parser_then_validator_in_order(self) -> None:
        parsed_result = make_result()
        use_case, generator, parser, validator, _audit, _reasoning = _use_case(
            parser=FakePathologyInterpretationParserPort(result=parsed_result)
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

        await use_case.execute(_input(output_format=PathologyOutputFormat.MARKDOWN))

        assert parser.received[0][1] is PathologyOutputFormat.MARKDOWN

    async def test_escalates_findings_via_the_clinical_correlator(self) -> None:
        parsed_result = make_result(
            microscopic_findings=(make_finding(category=PathologyFindingCategory.ATYPICAL),)
        )
        correlator = FakeClinicalCorrelationPort(classification=PathologyFindingCategory.MALIGNANT)
        use_case, *_rest, _reasoning = _use_case(
            parser=FakePathologyInterpretationParserPort(result=parsed_result),
            correlator=correlator,
        )

        generated = await use_case.execute(_input())

        assert generated.result.microscopic_findings[0].category is (
            PathologyFindingCategory.MALIGNANT
        )

    async def test_merges_findings_missed_by_the_ai(self) -> None:
        parsed_result = make_result(
            microscopic_findings=(
                make_finding(
                    description="Reactive changes", category=PathologyFindingCategory.BENIGN
                ),
            )
        )
        missed_candidate = make_finding(
            description="Carcinoma", category=PathologyFindingCategory.MALIGNANT
        )
        correlator = FakeClinicalCorrelationPort(candidates=(missed_candidate,))
        use_case, *_rest, _reasoning = _use_case(
            parser=FakePathologyInterpretationParserPort(result=parsed_result),
            correlator=correlator,
        )

        generated = await use_case.execute(_input())

        descriptions = {f.description for f in generated.result.microscopic_findings}
        assert "Carcinoma" in descriptions
        assert "Reactive changes" in descriptions

    async def test_derives_and_merges_correlation_follow_up_and_referral_for_malignant_findings(
        self,
    ) -> None:
        parsed_result = make_result(
            microscopic_findings=(
                make_finding(
                    description="Invasive carcinoma", category=PathologyFindingCategory.MALIGNANT
                ),
            ),
            correlation_recommendations=("Existing correlation",),
        )
        use_case, *_rest, _reasoning = _use_case(
            parser=FakePathologyInterpretationParserPort(result=parsed_result)
        )

        generated = await use_case.execute(_input())

        assert "Existing correlation" in generated.result.correlation_recommendations
        assert (
            "Ancillary study correlation (IHC/molecular) recommended for: Invasive carcinoma"
            in generated.result.correlation_recommendations
        )
        assert (
            "Confirmatory follow-up recommended for malignant finding: Invasive carcinoma"
            in generated.result.suggested_follow_up
        )
        assert (
            "Urgent oncology referral recommended given malignant finding: Invasive carcinoma"
            in generated.result.suggested_specialist_referral
        )

    async def test_deduplicates_conclusion_lists(self) -> None:
        parsed_result = make_result(correlation_recommendations=("IHC panel", "ihc panel"))
        use_case, *_rest, _reasoning = _use_case(
            parser=FakePathologyInterpretationParserPort(result=parsed_result)
        )

        generated = await use_case.execute(_input())

        assert len(generated.result.correlation_recommendations) == 1

    async def test_scores_confidence_via_the_medical_reasoning_facade(self) -> None:
        parsed_result = make_result(
            confidence_score=None,
            microscopic_findings=(make_finding(), make_finding(description="Second finding")),
        )
        reasoning = FakeMedicalReasoningAIPort(confidence_value=0.61)
        use_case, *_rest, _reasoning = _use_case(
            parser=FakePathologyInterpretationParserPort(result=parsed_result),
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
            parser=FakePathologyInterpretationParserPort(result=parsed_result)
        )

        generated = await use_case.execute(_input())

        assert generated.result.confidence_score == 0.92


class TestInterpretPathologyReportUseCaseFailureModes:
    async def test_parsing_failure_raises_and_logs_a_failure(self) -> None:
        parser = FakePathologyInterpretationParserPort(
            error=InvalidPathologyInterpretationResponseFormatError("malformed JSON")
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(parser=parser)

        with pytest.raises(InvalidPathologyInterpretationResponseFormatError):
            await use_case.execute(_input())

        assert audit.failures[0]["stage"] == "parse_or_validate"
        assert (
            audit.failures[0]["error_code"] == "InvalidPathologyInterpretationResponseFormatError"
        )
        assert audit.sessions == []

    async def test_duplicate_finding_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakePathologyInterpretationValidatorPort(
            error=DuplicatePathologyFindingError("Carcinoma")
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            validator=validator
        )

        with pytest.raises(DuplicatePathologyFindingError):
            await use_case.execute(_input())

        assert audit.failures[0]["error_code"] == "DuplicatePathologyFindingError"

    async def test_hallucinated_finding_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakePathologyInterpretationValidatorPort(
            error=HallucinatedPathologyFindingError("pathology_summary", "[insert]")
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            validator=validator
        )

        with pytest.raises(HallucinatedPathologyFindingError):
            await use_case.execute(_input())

        assert audit.failures[0]["error_code"] == "HallucinatedPathologyFindingError"

    async def test_inconsistent_conclusions_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakePathologyInterpretationValidatorPort(
            error=InconsistentPathologyConclusionsError("suggested_follow_up", "Repeat biopsy")
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            validator=validator
        )

        with pytest.raises(InconsistentPathologyConclusionsError):
            await use_case.execute(_input())

        assert audit.failures[0]["error_code"] == "InconsistentPathologyConclusionsError"

    async def test_invalid_confidence_value_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakePathologyInterpretationValidatorPort(
            error=InvalidPathologyConfidenceValueError()
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            validator=validator
        )

        with pytest.raises(InvalidPathologyConfidenceValueError):
            await use_case.execute(_input())

        assert audit.failures[0]["error_code"] == "InvalidPathologyConfidenceValueError"

    async def test_ai_foundation_errors_from_the_generator_propagate_unwrapped(self) -> None:
        class _FakeFoundationError(Exception):
            pass

        generator = FakePathologyInterpreterPort(error=_FakeFoundationError("provider down"))
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
        generator = FakePathologyInterpreterPort(session=session)
        parser = FakePathologyInterpretationParserPort(
            error=InvalidPathologyInterpretationResponseFormatError("x")
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            generator=generator, parser=parser
        )

        with pytest.raises(InvalidPathologyInterpretationResponseFormatError):
            await use_case.execute(_input())

        assert audit.failures[0]["generation_id"] == session.generation_id
