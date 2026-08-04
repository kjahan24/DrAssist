"""Unit tests for `GenerateClinicalReasoningUseCase`."""

from uuid import uuid4

import pytest

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
    EvidencePolarity,
    MedicalReasoningOutputFormat,
    ReasoningSetting,
    RedFlagPriority,
)
from app.modules.medical_reasoning_ai.domain.exceptions import (
    DuplicateEvidenceError,
    EmptyReasoningResponseError,
    HallucinatedReasoningPlaceholderError,
    InvalidMedicalReasoningResponseFormatError,
)
from app.modules.medical_reasoning_ai.domain.value_objects import (
    MedicalReasoningInput,
    RedFlag,
)
from tests.unit.modules.medical_reasoning_ai.application.fakes import (
    FakeConfidenceCalculatorPort,
    FakeEvidenceAnalyzerPort,
    FakeMedicalReasoningAuditLoggerPort,
    FakeMedicalReasoningParserPort,
    FakeMedicalReasoningPort,
    FakeMedicalReasoningValidatorPort,
    make_evidence_item,
    make_generation_session,
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


def _use_case(
    *,
    generator: FakeMedicalReasoningPort | None = None,
    parser: FakeMedicalReasoningParserPort | None = None,
    validator: FakeMedicalReasoningValidatorPort | None = None,
    audit_logger: FakeMedicalReasoningAuditLoggerPort | None = None,
    evidence_analyzer: FakeEvidenceAnalyzerPort | None = None,
    confidence_calculator: FakeConfidenceCalculatorPort | None = None,
) -> tuple[
    GenerateClinicalReasoningUseCase,
    FakeMedicalReasoningPort,
    FakeMedicalReasoningParserPort,
    FakeMedicalReasoningValidatorPort,
    FakeMedicalReasoningAuditLoggerPort,
]:
    generator = generator or FakeMedicalReasoningPort()
    parser = parser or FakeMedicalReasoningParserPort()
    validator = validator or FakeMedicalReasoningValidatorPort()
    audit_logger = audit_logger or FakeMedicalReasoningAuditLoggerPort()
    evidence_service = EvidenceAnalysisService(
        analyzer=evidence_analyzer or FakeEvidenceAnalyzerPort()
    )
    confidence_service = ConfidenceScoringService(
        calculator=confidence_calculator or FakeConfidenceCalculatorPort()
    )
    recommendation_service = RecommendationReasoningService()
    use_case = GenerateClinicalReasoningUseCase(
        generator=generator,
        parser=parser,
        validator=validator,
        evidence_service=evidence_service,
        confidence_service=confidence_service,
        recommendation_service=recommendation_service,
        audit_logger=audit_logger,
    )
    return use_case, generator, parser, validator, audit_logger


class TestGenerateClinicalReasoningUseCaseHappyPath:
    async def test_returns_result_and_session(self) -> None:
        use_case, *_ = _use_case()

        result = await use_case.execute(_evidence())

        assert result.result is not None
        assert result.session is not None

    async def test_calls_generator_then_parser_then_validator_in_order(self) -> None:
        parsed_result = make_result()
        use_case, generator, parser, validator, _audit = _use_case(
            parser=FakeMedicalReasoningParserPort(result=parsed_result)
        )
        evidence = _evidence()

        await use_case.execute(evidence)

        assert generator.received_evidence == [evidence]
        assert parser.received[0][0] == generator._raw_text
        assert validator.received == [parsed_result]

    async def test_logs_a_generation_session_on_success(self) -> None:
        use_case, _generator, _parser, _validator, audit = _use_case()

        await use_case.execute(_evidence())

        assert len(audit.sessions) == 1
        assert audit.failures == []

    async def test_passes_output_format_through_to_the_parser(self) -> None:
        use_case, _generator, parser, _validator, _audit = _use_case()

        await use_case.execute(_evidence(output_format=MedicalReasoningOutputFormat.MARKDOWN))

        assert parser.received[0][1] is MedicalReasoningOutputFormat.MARKDOWN

    async def test_fills_in_missing_confidence_via_the_confidence_calculator(self) -> None:
        parsed_result = make_result(
            clinical_confidence=None, diagnostic_confidence=None, therapeutic_confidence=None
        )
        calculator = FakeConfidenceCalculatorPort(fallback_value=0.33)
        use_case, *_ = _use_case(
            parser=FakeMedicalReasoningParserPort(result=parsed_result),
            confidence_calculator=calculator,
        )

        result = await use_case.execute(_evidence())

        assert result.result.clinical_confidence == 0.33
        assert result.result.diagnostic_confidence == 0.33
        assert result.result.therapeutic_confidence == 0.33

    async def test_preserves_ai_reported_confidence(self) -> None:
        parsed_result = make_result(
            clinical_confidence=0.9, diagnostic_confidence=0.8, therapeutic_confidence=0.7
        )
        use_case, *_ = _use_case(parser=FakeMedicalReasoningParserPort(result=parsed_result))

        result = await use_case.execute(_evidence())

        assert result.result.clinical_confidence == 0.9
        assert result.result.diagnostic_confidence == 0.8
        assert result.result.therapeutic_confidence == 0.7

    async def test_weights_evidence_via_the_evidence_analyzer(self) -> None:
        parsed_result = make_result(evidence=(make_evidence_item(description="Fever", weight=0.5),))
        analyzer = FakeEvidenceAnalyzerPort(weight_boost=0.2)
        use_case, *_ = _use_case(
            parser=FakeMedicalReasoningParserPort(result=parsed_result), evidence_analyzer=analyzer
        )

        result = await use_case.execute(_evidence())

        assert result.result.evidence[0].weight == pytest.approx(0.7)

    async def test_merges_missing_information_from_the_evidence_analyzer(self) -> None:
        parsed_result = make_result(missing_information=("AI-reported gap",))
        analyzer = FakeEvidenceAnalyzerPort(missing_information=("Deterministic gap",))
        use_case, *_ = _use_case(
            parser=FakeMedicalReasoningParserPort(result=parsed_result), evidence_analyzer=analyzer
        )

        result = await use_case.execute(_evidence())

        assert "AI-reported gap" in result.result.missing_information
        assert "Deterministic gap" in result.result.missing_information

    async def test_escalates_red_flags_when_risk_score_is_high(self) -> None:
        parsed_result = make_result(
            red_flags=(RedFlag(description="Hypotension", priority=RedFlagPriority.LOW),)
        )
        analyzer = FakeEvidenceAnalyzerPort(risk_score=0.9)
        use_case, *_ = _use_case(
            parser=FakeMedicalReasoningParserPort(result=parsed_result), evidence_analyzer=analyzer
        )

        result = await use_case.execute(_evidence())

        assert result.result.red_flags[0].priority is RedFlagPriority.MODERATE

    async def test_deduplicates_recommendation_lists(self) -> None:
        parsed_result = make_result(suggested_investigations=("CBC", "cbc "))
        use_case, *_ = _use_case(parser=FakeMedicalReasoningParserPort(result=parsed_result))

        result = await use_case.execute(_evidence())

        assert len(result.result.suggested_investigations) == 1


class TestGenerateClinicalReasoningUseCaseFailureModes:
    async def test_parsing_failure_raises_and_logs_a_failure(self) -> None:
        parser = FakeMedicalReasoningParserPort(
            error=InvalidMedicalReasoningResponseFormatError("malformed JSON")
        )
        use_case, _generator, _parser, _validator, audit = _use_case(parser=parser)

        with pytest.raises(InvalidMedicalReasoningResponseFormatError):
            await use_case.execute(_evidence())

        assert audit.failures[0]["stage"] == "parse_or_validate"
        assert audit.failures[0]["error_code"] == "InvalidMedicalReasoningResponseFormatError"
        assert audit.sessions == []

    async def test_empty_response_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeMedicalReasoningValidatorPort(error=EmptyReasoningResponseError())
        use_case, _generator, _parser, _validator, audit = _use_case(validator=validator)

        with pytest.raises(EmptyReasoningResponseError):
            await use_case.execute(_evidence())

        assert audit.failures[0]["error_code"] == "EmptyReasoningResponseError"

    async def test_duplicate_evidence_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeMedicalReasoningValidatorPort(error=DuplicateEvidenceError("Fever"))
        use_case, _generator, _parser, _validator, audit = _use_case(validator=validator)

        with pytest.raises(DuplicateEvidenceError):
            await use_case.execute(_evidence())

        assert audit.failures[0]["error_code"] == "DuplicateEvidenceError"

    async def test_hallucinated_placeholder_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeMedicalReasoningValidatorPort(
            error=HallucinatedReasoningPlaceholderError("clinical_summary", "[INSERT]")
        )
        use_case, _generator, _parser, _validator, audit = _use_case(validator=validator)

        with pytest.raises(HallucinatedReasoningPlaceholderError):
            await use_case.execute(_evidence())

        assert audit.failures[0]["error_code"] == "HallucinatedReasoningPlaceholderError"

    async def test_ai_foundation_errors_from_the_generator_propagate_unwrapped(self) -> None:
        class _FakeFoundationError(Exception):
            pass

        generator = FakeMedicalReasoningPort(error=_FakeFoundationError("provider down"))
        use_case, _generator, _parser, _validator, audit = _use_case(generator=generator)

        with pytest.raises(_FakeFoundationError):
            await use_case.execute(_evidence())

        assert audit.failures == []
        assert audit.sessions == []

    async def test_generation_id_on_failure_log_matches_the_session_from_the_generator(
        self,
    ) -> None:
        session = make_generation_session()
        generator = FakeMedicalReasoningPort(session=session)
        parser = FakeMedicalReasoningParserPort(
            error=InvalidMedicalReasoningResponseFormatError("x")
        )
        use_case, _generator, _parser, _validator, audit = _use_case(
            generator=generator, parser=parser
        )

        with pytest.raises(InvalidMedicalReasoningResponseFormatError):
            await use_case.execute(_evidence())

        assert audit.failures[0]["generation_id"] == session.generation_id


class TestGenerateClinicalReasoningUseCaseEvidencePolarityPreserved:
    async def test_supporting_and_contradicting_split_survives_enrichment(self) -> None:
        parsed_result = make_result(
            evidence=(
                make_evidence_item(
                    description="Elevated troponin", polarity=EvidencePolarity.SUPPORTING
                ),
                make_evidence_item(
                    description="Normal ECG", polarity=EvidencePolarity.CONTRADICTING
                ),
            )
        )
        use_case, *_ = _use_case(parser=FakeMedicalReasoningParserPort(result=parsed_result))

        result = await use_case.execute(_evidence())

        assert len(result.result.supporting_evidence) == 1
        assert len(result.result.contradicting_evidence) == 1
