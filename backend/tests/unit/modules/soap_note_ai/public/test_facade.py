"""Unit tests for `SOAPNoteAIFacade` — exercised through `SOAPNoteAIPort`
exactly as a future consumer module would call it, per
`docs/backend-architecture/12_testing_architecture.md`'s "Contract tests"
framing."""

from uuid import uuid4

from app.modules.soap_note_ai.application.services.soap_note_renderer import SOAPNoteRenderer
from app.modules.soap_note_ai.application.use_cases.generate_soap_note import (
    GenerateSOAPNoteUseCase,
)
from app.modules.soap_note_ai.application.use_cases.render_soap_note import RenderSOAPNoteUseCase
from app.modules.soap_note_ai.application.use_cases.validate_soap_input import (
    ValidateSOAPInputUseCase,
)
from app.modules.soap_note_ai.domain.enums import SOAPNoteOutputFormat, SOAPStyle
from app.modules.soap_note_ai.public.dto import SOAPEncounterInput
from app.modules.soap_note_ai.public.facade import SOAPNoteAIFacade
from app.modules.soap_note_ai.public.interfaces import SOAPNoteAIPort
from tests.unit.modules.soap_note_ai.application.fakes import (
    FakeSOAPGeneratorPort,
    FakeSOAPNoteAuditLoggerPort,
    FakeSOAPNoteParserPort,
    FakeSOAPNoteValidatorPort,
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


def _facade(*, generator: FakeSOAPGeneratorPort | None = None) -> SOAPNoteAIFacade:
    generator = generator or FakeSOAPGeneratorPort()
    generate_use_case = GenerateSOAPNoteUseCase(
        generator=generator,
        parser=FakeSOAPNoteParserPort(result=make_soap_note()),
        validator=FakeSOAPNoteValidatorPort(),
        audit_logger=FakeSOAPNoteAuditLoggerPort(),
    )
    return SOAPNoteAIFacade(
        generate_use_case=generate_use_case,
        validate_use_case=ValidateSOAPInputUseCase(),
        render_use_case=RenderSOAPNoteUseCase(renderer=SOAPNoteRenderer()),
        generator=generator,
    )


class TestSOAPNoteAIFacade:
    def test_is_a_soap_note_ai_port(self) -> None:
        assert isinstance(_facade(), SOAPNoteAIPort)

    async def test_generate_note_delegates_to_the_use_case(self) -> None:
        facade = _facade()

        result = await facade.generate_note(_encounter())

        assert result.note is not None
        assert result.session is not None

    async def test_stream_generate_note_delegates_to_the_generator(self) -> None:
        generator = FakeSOAPGeneratorPort(raw_text="hello world")
        facade = _facade(generator=generator)

        chunks = [chunk async for chunk in facade.stream_generate_note(_encounter())]

        assert "".join(c.delta for c in chunks) == "hello world"

    async def test_render_note_delegates_to_the_renderer(self) -> None:
        facade = _facade()
        note = make_soap_note()

        rendered = await facade.render_note(note, target_format=SOAPNoteOutputFormat.TEXT)

        assert "SUBJECTIVE:" in rendered

    async def test_validate_input_delegates_to_the_use_case(self) -> None:
        facade = _facade()

        result = await facade.validate_input(_encounter())

        assert result.is_valid is True
