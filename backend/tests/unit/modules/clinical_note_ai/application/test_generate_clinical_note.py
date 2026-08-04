"""Unit tests for `GenerateClinicalNoteUseCase`."""

from uuid import uuid4

import pytest

from app.modules.clinical_note_ai.application.use_cases.generate_clinical_note import (
    GenerateClinicalNoteUseCase,
)
from app.modules.clinical_note_ai.domain.enums import NoteStyle
from app.modules.clinical_note_ai.domain.exceptions import (
    HallucinatedPlaceholderError,
    InvalidClinicalNoteFormatError,
    MissingClinicalNoteSectionError,
)
from app.modules.clinical_note_ai.domain.value_objects import ClinicalEncounterInput
from tests.unit.modules.clinical_note_ai.application.fakes import (
    FakeClinicalNoteAuditLoggerPort,
    FakeClinicalNoteGeneratorPort,
    FakeClinicalNoteParserPort,
    FakeClinicalNoteValidatorPort,
    make_clinical_note,
)


def _encounter(**overrides: object) -> ClinicalEncounterInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Headache",
        "note_style": NoteStyle.CONCISE,
    }
    defaults.update(overrides)
    return ClinicalEncounterInput(**defaults)  # type: ignore[arg-type]


def _use_case(
    *,
    generator: FakeClinicalNoteGeneratorPort | None = None,
    parser: FakeClinicalNoteParserPort | None = None,
    validator: FakeClinicalNoteValidatorPort | None = None,
    audit_logger: FakeClinicalNoteAuditLoggerPort | None = None,
) -> tuple[
    GenerateClinicalNoteUseCase,
    FakeClinicalNoteGeneratorPort,
    FakeClinicalNoteParserPort,
    FakeClinicalNoteValidatorPort,
    FakeClinicalNoteAuditLoggerPort,
]:
    generator = generator or FakeClinicalNoteGeneratorPort()
    parser = parser or FakeClinicalNoteParserPort()
    validator = validator or FakeClinicalNoteValidatorPort()
    audit_logger = audit_logger or FakeClinicalNoteAuditLoggerPort()
    use_case = GenerateClinicalNoteUseCase(
        generator=generator, parser=parser, validator=validator, audit_logger=audit_logger
    )
    return use_case, generator, parser, validator, audit_logger


class TestGenerateClinicalNoteUseCaseHappyPath:
    async def test_returns_generated_note_and_session(self) -> None:
        use_case, *_ = _use_case()

        result = await use_case.execute(_encounter())

        assert result.note is not None
        assert result.session is not None

    async def test_calls_generator_then_parser_then_validator_in_order(self) -> None:
        note = make_clinical_note()
        use_case, generator, parser, validator, _audit = _use_case(
            parser=FakeClinicalNoteParserPort(result=note)
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
        from app.modules.clinical_note_ai.domain.enums import ClinicalNoteOutputFormat

        use_case, _generator, parser, _validator, _audit = _use_case()

        await use_case.execute(_encounter(output_format=ClinicalNoteOutputFormat.MARKDOWN))

        assert parser.received[0][1] is ClinicalNoteOutputFormat.MARKDOWN


class TestGenerateClinicalNoteUseCaseFailureModes:
    async def test_parsing_failure_raises_and_logs_a_failure(self) -> None:
        parser = FakeClinicalNoteParserPort(error=InvalidClinicalNoteFormatError("malformed JSON"))
        use_case, _generator, _parser, _validator, audit = _use_case(parser=parser)

        with pytest.raises(InvalidClinicalNoteFormatError):
            await use_case.execute(_encounter())

        assert audit.failures[0]["stage"] == "parse_or_validate"
        assert audit.failures[0]["error_code"] == "InvalidClinicalNoteFormatError"
        assert audit.sessions == []

    async def test_missing_section_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeClinicalNoteValidatorPort(
            error=MissingClinicalNoteSectionError("assessment")
        )
        use_case, _generator, _parser, _validator, audit = _use_case(validator=validator)

        with pytest.raises(MissingClinicalNoteSectionError):
            await use_case.execute(_encounter())

        assert audit.failures[0]["error_code"] == "MissingClinicalNoteSectionError"

    async def test_hallucinated_placeholder_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeClinicalNoteValidatorPort(
            error=HallucinatedPlaceholderError("plan", "[INSERT]")
        )
        use_case, _generator, _parser, _validator, audit = _use_case(validator=validator)

        with pytest.raises(HallucinatedPlaceholderError):
            await use_case.execute(_encounter())

        assert audit.failures[0]["error_code"] == "HallucinatedPlaceholderError"

    async def test_ai_foundation_errors_from_the_generator_propagate_unwrapped(self) -> None:
        class _FakeFoundationError(Exception):
            pass

        generator = FakeClinicalNoteGeneratorPort(error=_FakeFoundationError("provider down"))
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
        from tests.unit.modules.clinical_note_ai.application.fakes import make_generation_session

        session = make_generation_session()
        generator = FakeClinicalNoteGeneratorPort(session=session)
        parser = FakeClinicalNoteParserPort(error=InvalidClinicalNoteFormatError("x"))
        use_case, _generator, _parser, _validator, audit = _use_case(
            generator=generator, parser=parser
        )

        with pytest.raises(InvalidClinicalNoteFormatError):
            await use_case.execute(_encounter())

        assert audit.failures[0]["generation_id"] == session.generation_id
