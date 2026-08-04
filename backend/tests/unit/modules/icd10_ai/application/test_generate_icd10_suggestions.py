"""Unit tests for `GenerateICD10SuggestionsUseCase`."""

from uuid import uuid4

import pytest

from app.modules.icd10_ai.application.services.icd10_ranking_service import ICD10RankingService
from app.modules.icd10_ai.application.use_cases.generate_icd10_suggestions import (
    GenerateICD10SuggestionsUseCase,
)
from app.modules.icd10_ai.domain.enums import CodingSetting, ICD10OutputFormat
from app.modules.icd10_ai.domain.exceptions import (
    EmptyICD10ResponseError,
    HallucinatedDiagnosisError,
    InvalidICD10CodeError,
    InvalidICD10ResponseFormatError,
)
from app.modules.icd10_ai.domain.value_objects import ICD10CodingInput
from tests.unit.modules.icd10_ai.application.fakes import (
    FakeICD10AuditLoggerPort,
    FakeICD10GeneratorPort,
    FakeICD10KnowledgePort,
    FakeICD10SuggestionParserPort,
    FakeICD10SuggestionValidatorPort,
    make_generation_session,
    make_suggestion_set,
)


def _coding_input(**overrides: object) -> ICD10CodingInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Sore throat",
        "coding_setting": CodingSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return ICD10CodingInput(**defaults)  # type: ignore[arg-type]


def _use_case(
    *,
    generator: FakeICD10GeneratorPort | None = None,
    parser: FakeICD10SuggestionParserPort | None = None,
    validator: FakeICD10SuggestionValidatorPort | None = None,
    audit_logger: FakeICD10AuditLoggerPort | None = None,
) -> tuple[
    GenerateICD10SuggestionsUseCase,
    FakeICD10GeneratorPort,
    FakeICD10SuggestionParserPort,
    FakeICD10SuggestionValidatorPort,
    FakeICD10AuditLoggerPort,
]:
    generator = generator or FakeICD10GeneratorPort()
    parser = parser or FakeICD10SuggestionParserPort()
    validator = validator or FakeICD10SuggestionValidatorPort()
    audit_logger = audit_logger or FakeICD10AuditLoggerPort()
    ranking_service = ICD10RankingService(knowledge=FakeICD10KnowledgePort())
    use_case = GenerateICD10SuggestionsUseCase(
        generator=generator,
        parser=parser,
        validator=validator,
        ranking_service=ranking_service,
        audit_logger=audit_logger,
    )
    return use_case, generator, parser, validator, audit_logger


class TestGenerateICD10SuggestionsUseCaseHappyPath:
    async def test_returns_suggestions_and_session(self) -> None:
        use_case, *_ = _use_case()

        result = await use_case.execute(_coding_input())

        assert result.suggestions is not None
        assert result.session is not None

    async def test_calls_generator_then_parser_then_validator_in_order(self) -> None:
        suggestion_set = make_suggestion_set()
        use_case, generator, parser, validator, _audit = _use_case(
            parser=FakeICD10SuggestionParserPort(result=suggestion_set)
        )
        coding_input = _coding_input()

        result = await use_case.execute(coding_input)

        assert generator.received_inputs == [coding_input]
        assert parser.received[0][0] == generator._raw_text
        assert validator.received == [suggestion_set]
        assert result.suggestions.suggestions == suggestion_set.suggestions

    async def test_logs_a_generation_session_on_success(self) -> None:
        use_case, _generator, _parser, _validator, audit = _use_case()

        await use_case.execute(_coding_input())

        assert len(audit.sessions) == 1
        assert audit.failures == []

    async def test_passes_output_format_through_to_the_parser(self) -> None:
        use_case, _generator, parser, _validator, _audit = _use_case()

        await use_case.execute(_coding_input(output_format=ICD10OutputFormat.MARKDOWN))

        assert parser.received[0][1] is ICD10OutputFormat.MARKDOWN


class TestGenerateICD10SuggestionsUseCaseFailureModes:
    async def test_parsing_failure_raises_and_logs_a_failure(self) -> None:
        parser = FakeICD10SuggestionParserPort(
            error=InvalidICD10ResponseFormatError("malformed JSON")
        )
        use_case, _generator, _parser, _validator, audit = _use_case(parser=parser)

        with pytest.raises(InvalidICD10ResponseFormatError):
            await use_case.execute(_coding_input())

        assert audit.failures[0]["stage"] == "parse_or_validate"
        assert audit.failures[0]["error_code"] == "InvalidICD10ResponseFormatError"
        assert audit.sessions == []

    async def test_empty_response_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeICD10SuggestionValidatorPort(error=EmptyICD10ResponseError())
        use_case, _generator, _parser, _validator, audit = _use_case(validator=validator)

        with pytest.raises(EmptyICD10ResponseError):
            await use_case.execute(_coding_input())

        assert audit.failures[0]["error_code"] == "EmptyICD10ResponseError"

    async def test_invalid_code_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeICD10SuggestionValidatorPort(error=InvalidICD10CodeError("XYZ"))
        use_case, _generator, _parser, _validator, audit = _use_case(validator=validator)

        with pytest.raises(InvalidICD10CodeError):
            await use_case.execute(_coding_input())

        assert audit.failures[0]["error_code"] == "InvalidICD10CodeError"

    async def test_hallucinated_diagnosis_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeICD10SuggestionValidatorPort(
            error=HallucinatedDiagnosisError("J06.9", "[INSERT]")
        )
        use_case, _generator, _parser, _validator, audit = _use_case(validator=validator)

        with pytest.raises(HallucinatedDiagnosisError):
            await use_case.execute(_coding_input())

        assert audit.failures[0]["error_code"] == "HallucinatedDiagnosisError"

    async def test_ai_foundation_errors_from_the_generator_propagate_unwrapped(self) -> None:
        class _FakeFoundationError(Exception):
            pass

        generator = FakeICD10GeneratorPort(error=_FakeFoundationError("provider down"))
        use_case, _generator, _parser, _validator, audit = _use_case(generator=generator)

        with pytest.raises(_FakeFoundationError):
            await use_case.execute(_coding_input())

        # This module does not catch/log AI-Foundation-originated errors —
        # no failure record is expected here (see the use case's own
        # module docstring).
        assert audit.failures == []
        assert audit.sessions == []

    async def test_generation_id_on_failure_log_matches_the_session_from_the_generator(
        self,
    ) -> None:
        session = make_generation_session()
        generator = FakeICD10GeneratorPort(session=session)
        parser = FakeICD10SuggestionParserPort(error=InvalidICD10ResponseFormatError("x"))
        use_case, _generator, _parser, _validator, audit = _use_case(
            generator=generator, parser=parser
        )

        with pytest.raises(InvalidICD10ResponseFormatError):
            await use_case.execute(_coding_input())

        assert audit.failures[0]["generation_id"] == session.generation_id
