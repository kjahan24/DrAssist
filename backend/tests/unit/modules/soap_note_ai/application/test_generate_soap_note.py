"""Unit tests for `GenerateSOAPNoteUseCase`."""

from uuid import uuid4

import pytest

from app.modules.soap_note_ai.application.use_cases.generate_soap_note import (
    GenerateSOAPNoteUseCase,
)
from app.modules.soap_note_ai.domain.enums import SOAPNoteOutputFormat, SOAPStyle
from app.modules.soap_note_ai.domain.exceptions import (
    HallucinatedPlaceholderError,
    InvalidSOAPNoteFormatError,
    MissingSOAPSectionError,
)
from app.modules.soap_note_ai.domain.value_objects import SOAPEncounterInput
from tests.unit.modules.soap_note_ai.application.fakes import (
    FakeSOAPGeneratorPort,
    FakeSOAPNoteAuditLoggerPort,
    FakeSOAPNoteParserPort,
    FakeSOAPNoteValidatorPort,
    make_generation_session,
    make_soap_note,
)


def _encounter(**overrides: object) -> SOAPEncounterInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Headache",
        "soap_style": SOAPStyle.STANDARD,
    }
    defaults.update(overrides)
    return SOAPEncounterInput(**defaults)  # type: ignore[arg-type]


def _use_case(
    *,
    generator: FakeSOAPGeneratorPort | None = None,
    parser: FakeSOAPNoteParserPort | None = None,
    validator: FakeSOAPNoteValidatorPort | None = None,
    audit_logger: FakeSOAPNoteAuditLoggerPort | None = None,
) -> tuple[
    GenerateSOAPNoteUseCase,
    FakeSOAPGeneratorPort,
    FakeSOAPNoteParserPort,
    FakeSOAPNoteValidatorPort,
    FakeSOAPNoteAuditLoggerPort,
]:
    generator = generator or FakeSOAPGeneratorPort()
    parser = parser or FakeSOAPNoteParserPort()
    validator = validator or FakeSOAPNoteValidatorPort()
    audit_logger = audit_logger or FakeSOAPNoteAuditLoggerPort()
    use_case = GenerateSOAPNoteUseCase(
        generator=generator, parser=parser, validator=validator, audit_logger=audit_logger
    )
    return use_case, generator, parser, validator, audit_logger


class TestGenerateSOAPNoteUseCaseHappyPath:
    async def test_returns_generated_note_and_session(self) -> None:
        use_case, *_ = _use_case()

        result = await use_case.execute(_encounter())

        assert result.note is not None
        assert result.session is not None

    async def test_calls_generator_then_parser_then_validator_in_order(self) -> None:
        note = make_soap_note()
        use_case, generator, parser, validator, _audit = _use_case(
            parser=FakeSOAPNoteParserPort(result=note)
        )
        encounter = _encounter()

        result = await use_case.execute(encounter)

        assert generator.received_encounters == [encounter]
        assert parser.received[0][0] == generator._raw_text
        assert validator.received == [note]
        assert result.note is note

    async def test_logs_a_generation_session_on_success(self) -> None:
        use_case, _generator, _parser, _validator, audit = _use_case()

        await use_case.execute(_encounter())

        assert len(audit.sessions) == 1
        assert audit.failures == []

    async def test_passes_output_format_through_to_the_parser(self) -> None:
        use_case, _generator, parser, _validator, _audit = _use_case()

        await use_case.execute(_encounter(output_format=SOAPNoteOutputFormat.MARKDOWN))

        assert parser.received[0][1] is SOAPNoteOutputFormat.MARKDOWN


class TestGenerateSOAPNoteUseCaseFailureModes:
    async def test_parsing_failure_raises_and_logs_a_failure(self) -> None:
        parser = FakeSOAPNoteParserPort(error=InvalidSOAPNoteFormatError("malformed JSON"))
        use_case, _generator, _parser, _validator, audit = _use_case(parser=parser)

        with pytest.raises(InvalidSOAPNoteFormatError):
            await use_case.execute(_encounter())

        assert audit.failures[0]["stage"] == "parse_or_validate"
        assert audit.failures[0]["error_code"] == "InvalidSOAPNoteFormatError"
        assert audit.sessions == []

    async def test_missing_section_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeSOAPNoteValidatorPort(error=MissingSOAPSectionError("plan"))
        use_case, _generator, _parser, _validator, audit = _use_case(validator=validator)

        with pytest.raises(MissingSOAPSectionError):
            await use_case.execute(_encounter())

        assert audit.failures[0]["error_code"] == "MissingSOAPSectionError"

    async def test_hallucinated_placeholder_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeSOAPNoteValidatorPort(
            error=HallucinatedPlaceholderError("plan", "[INSERT]")
        )
        use_case, _generator, _parser, _validator, audit = _use_case(validator=validator)

        with pytest.raises(HallucinatedPlaceholderError):
            await use_case.execute(_encounter())

        assert audit.failures[0]["error_code"] == "HallucinatedPlaceholderError"

    async def test_ai_foundation_errors_from_the_generator_propagate_unwrapped(self) -> None:
        class _FakeFoundationError(Exception):
            pass

        generator = FakeSOAPGeneratorPort(error=_FakeFoundationError("provider down"))
        use_case, _generator, _parser, _validator, audit = _use_case(generator=generator)

        with pytest.raises(_FakeFoundationError):
            await use_case.execute(_encounter())

        # This module does not catch/log AI-Foundation-originated errors —
        # no failure record is expected here (see the use case's own
        # module docstring).
        assert audit.failures == []
        assert audit.sessions == []

    async def test_generation_id_on_failure_log_matches_the_session_from_the_generator(
        self,
    ) -> None:
        session = make_generation_session()
        generator = FakeSOAPGeneratorPort(session=session)
        parser = FakeSOAPNoteParserPort(error=InvalidSOAPNoteFormatError("x"))
        use_case, _generator, _parser, _validator, audit = _use_case(
            generator=generator, parser=parser
        )

        with pytest.raises(InvalidSOAPNoteFormatError):
            await use_case.execute(_encounter())

        assert audit.failures[0]["generation_id"] == session.generation_id
