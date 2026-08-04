"""Unit tests for `GenerateDifferentialDiagnosisUseCase`."""

from uuid import uuid4

import pytest

from app.modules.differential_diagnosis_ai.application.services.clinical_reasoning_service import (
    ClinicalReasoningService,
)
from app.modules.differential_diagnosis_ai.application.services.differential_diagnosis_ranking_service import (  # noqa: E501
    DifferentialDiagnosisRankingService,
)
from app.modules.differential_diagnosis_ai.application.use_cases.generate_differential_diagnosis import (  # noqa: E501
    GenerateDifferentialDiagnosisUseCase,
)
from app.modules.differential_diagnosis_ai.domain.enums import (
    ClinicalSetting,
    DifferentialOutputFormat,
    UrgencyLevel,
)
from app.modules.differential_diagnosis_ai.domain.exceptions import (
    DuplicateDiagnosisError,
    EmptyDifferentialResponseError,
    HallucinatedDiagnosisError,
    InvalidDifferentialResponseFormatError,
)
from app.modules.differential_diagnosis_ai.domain.value_objects import DifferentialDiagnosisInput
from tests.unit.modules.differential_diagnosis_ai.application.fakes import (
    FakeClinicalReasoningPort,
    FakeDifferentialDiagnosisAuditLoggerPort,
    FakeDifferentialDiagnosisGeneratorPort,
    FakeDifferentialDiagnosisParserPort,
    FakeDifferentialDiagnosisValidatorPort,
    make_candidate,
    make_generation_session,
    make_result,
)


def _evidence(**overrides: object) -> DifferentialDiagnosisInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Chest pain",
        "clinical_setting": ClinicalSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return DifferentialDiagnosisInput(**defaults)  # type: ignore[arg-type]


def _use_case(
    *,
    generator: FakeDifferentialDiagnosisGeneratorPort | None = None,
    parser: FakeDifferentialDiagnosisParserPort | None = None,
    validator: FakeDifferentialDiagnosisValidatorPort | None = None,
    audit_logger: FakeDifferentialDiagnosisAuditLoggerPort | None = None,
    reasoning_port: FakeClinicalReasoningPort | None = None,
) -> tuple[
    GenerateDifferentialDiagnosisUseCase,
    FakeDifferentialDiagnosisGeneratorPort,
    FakeDifferentialDiagnosisParserPort,
    FakeDifferentialDiagnosisValidatorPort,
    FakeDifferentialDiagnosisAuditLoggerPort,
]:
    generator = generator or FakeDifferentialDiagnosisGeneratorPort()
    parser = parser or FakeDifferentialDiagnosisParserPort()
    validator = validator or FakeDifferentialDiagnosisValidatorPort()
    audit_logger = audit_logger or FakeDifferentialDiagnosisAuditLoggerPort()
    reasoning_service = ClinicalReasoningService(
        reasoning=reasoning_port or FakeClinicalReasoningPort()
    )
    use_case = GenerateDifferentialDiagnosisUseCase(
        generator=generator,
        parser=parser,
        validator=validator,
        reasoning_service=reasoning_service,
        ranking_service=DifferentialDiagnosisRankingService(),
        audit_logger=audit_logger,
    )
    return use_case, generator, parser, validator, audit_logger


class TestGenerateDifferentialDiagnosisUseCaseHappyPath:
    async def test_returns_result_and_session(self) -> None:
        use_case, *_ = _use_case()

        result = await use_case.execute(_evidence())

        assert result.result is not None
        assert result.session is not None

    async def test_calls_generator_then_parser_then_validator_in_order(self) -> None:
        candidate = make_candidate(disease_name="Pneumonia")
        parsed_result = make_result(candidates=(candidate,))
        use_case, generator, parser, validator, _audit = _use_case(
            parser=FakeDifferentialDiagnosisParserPort(result=parsed_result)
        )
        evidence = _evidence()

        result = await use_case.execute(evidence)

        assert generator.received_evidence == [evidence]
        assert parser.received[0][0] == generator._raw_text
        assert validator.received == [parsed_result]
        assert result.result.candidates[0].disease_name == "Pneumonia"

    async def test_logs_a_generation_session_on_success(self) -> None:
        use_case, _generator, _parser, _validator, audit = _use_case()

        await use_case.execute(_evidence())

        assert len(audit.sessions) == 1
        assert audit.failures == []

    async def test_passes_output_format_through_to_the_parser(self) -> None:
        use_case, _generator, parser, _validator, _audit = _use_case()

        await use_case.execute(_evidence(output_format=DifferentialOutputFormat.MARKDOWN))

        assert parser.received[0][1] is DifferentialOutputFormat.MARKDOWN

    async def test_upgrades_urgency_when_red_flags_present(self) -> None:
        candidate = make_candidate(
            red_flag_indicators=("hypotension",), urgency_level=UrgencyLevel.ROUTINE
        )
        parsed_result = make_result(candidates=(candidate,))
        reasoning_port = FakeClinicalReasoningPort(minimum_urgency=UrgencyLevel.EMERGENT)
        use_case, *_ = _use_case(
            parser=FakeDifferentialDiagnosisParserPort(result=parsed_result),
            reasoning_port=reasoning_port,
        )

        result = await use_case.execute(_evidence())

        assert result.result.candidates[0].urgency_level is UrgencyLevel.EMERGENT

    async def test_ranks_candidates_by_confidence_as_the_final_step(self) -> None:
        low = make_candidate(disease_name="Bronchitis", confidence_score=0.2)
        high = make_candidate(disease_name="Pneumonia", confidence_score=0.9)
        parsed_result = make_result(candidates=(low, high))
        use_case, *_ = _use_case(parser=FakeDifferentialDiagnosisParserPort(result=parsed_result))

        result = await use_case.execute(_evidence())

        assert result.result.candidates[0].disease_name == "Pneumonia"


class TestGenerateDifferentialDiagnosisUseCaseFailureModes:
    async def test_parsing_failure_raises_and_logs_a_failure(self) -> None:
        parser = FakeDifferentialDiagnosisParserPort(
            error=InvalidDifferentialResponseFormatError("malformed JSON")
        )
        use_case, _generator, _parser, _validator, audit = _use_case(parser=parser)

        with pytest.raises(InvalidDifferentialResponseFormatError):
            await use_case.execute(_evidence())

        assert audit.failures[0]["stage"] == "parse_or_validate"
        assert audit.failures[0]["error_code"] == "InvalidDifferentialResponseFormatError"
        assert audit.sessions == []

    async def test_empty_response_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeDifferentialDiagnosisValidatorPort(error=EmptyDifferentialResponseError())
        use_case, _generator, _parser, _validator, audit = _use_case(validator=validator)

        with pytest.raises(EmptyDifferentialResponseError):
            await use_case.execute(_evidence())

        assert audit.failures[0]["error_code"] == "EmptyDifferentialResponseError"

    async def test_duplicate_diagnosis_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeDifferentialDiagnosisValidatorPort(
            error=DuplicateDiagnosisError("Pneumonia")
        )
        use_case, _generator, _parser, _validator, audit = _use_case(validator=validator)

        with pytest.raises(DuplicateDiagnosisError):
            await use_case.execute(_evidence())

        assert audit.failures[0]["error_code"] == "DuplicateDiagnosisError"

    async def test_hallucinated_diagnosis_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeDifferentialDiagnosisValidatorPort(
            error=HallucinatedDiagnosisError("Pneumonia", "[INSERT]")
        )
        use_case, _generator, _parser, _validator, audit = _use_case(validator=validator)

        with pytest.raises(HallucinatedDiagnosisError):
            await use_case.execute(_evidence())

        assert audit.failures[0]["error_code"] == "HallucinatedDiagnosisError"

    async def test_ai_foundation_errors_from_the_generator_propagate_unwrapped(self) -> None:
        class _FakeFoundationError(Exception):
            pass

        generator = FakeDifferentialDiagnosisGeneratorPort(
            error=_FakeFoundationError("provider down")
        )
        use_case, _generator, _parser, _validator, audit = _use_case(generator=generator)

        with pytest.raises(_FakeFoundationError):
            await use_case.execute(_evidence())

        # This module does not catch/log AI-Foundation-originated errors —
        # no failure record is expected here (see the use case's own
        # module docstring).
        assert audit.failures == []
        assert audit.sessions == []

    async def test_generation_id_on_failure_log_matches_the_session_from_the_generator(
        self,
    ) -> None:
        session = make_generation_session()
        generator = FakeDifferentialDiagnosisGeneratorPort(session=session)
        parser = FakeDifferentialDiagnosisParserPort(
            error=InvalidDifferentialResponseFormatError("x")
        )
        use_case, _generator, _parser, _validator, audit = _use_case(
            generator=generator, parser=parser
        )

        with pytest.raises(InvalidDifferentialResponseFormatError):
            await use_case.execute(_evidence())

        assert audit.failures[0]["generation_id"] == session.generation_id
