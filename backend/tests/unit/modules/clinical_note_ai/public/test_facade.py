"""Unit tests for `ClinicalNoteAIFacade` — exercised through
`ClinicalNoteAIPort` exactly as a future consumer module would call it,
per `docs/backend-architecture/12_testing_architecture.md`'s "Contract
tests" framing."""

from uuid import uuid4

from app.modules.clinical_note_ai.application.services.clinical_note_renderer import (
    ClinicalNoteRenderer,
)
from app.modules.clinical_note_ai.application.use_cases.generate_clinical_note import (
    GenerateClinicalNoteUseCase,
)
from app.modules.clinical_note_ai.application.use_cases.render_clinical_note import (
    RenderClinicalNoteUseCase,
)
from app.modules.clinical_note_ai.application.use_cases.validate_clinical_input import (
    ValidateClinicalInputUseCase,
)
from app.modules.clinical_note_ai.domain.enums import NoteStyle
from app.modules.clinical_note_ai.public.dto import ClinicalEncounterInput
from app.modules.clinical_note_ai.public.facade import ClinicalNoteAIFacade
from app.modules.clinical_note_ai.public.interfaces import ClinicalNoteAIPort
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


def _facade(*, generator: FakeClinicalNoteGeneratorPort | None = None) -> ClinicalNoteAIFacade:
    generator = generator or FakeClinicalNoteGeneratorPort()
    generate_use_case = GenerateClinicalNoteUseCase(
        generator=generator,
        parser=FakeClinicalNoteParserPort(result=make_clinical_note()),
        validator=FakeClinicalNoteValidatorPort(),
        audit_logger=FakeClinicalNoteAuditLoggerPort(),
    )
    return ClinicalNoteAIFacade(
        generate_use_case=generate_use_case,
        validate_use_case=ValidateClinicalInputUseCase(),
        render_use_case=RenderClinicalNoteUseCase(renderer=ClinicalNoteRenderer()),
        generator=generator,
    )


class TestClinicalNoteAIFacade:
    def test_is_a_clinical_note_ai_port(self) -> None:
        assert isinstance(_facade(), ClinicalNoteAIPort)

    async def test_generate_note_delegates_to_the_use_case(self) -> None:
        facade = _facade()

        result = await facade.generate_note(_encounter())

        assert result.note is not None
        assert result.session is not None

    async def test_stream_generate_note_delegates_to_the_generator(self) -> None:
        generator = FakeClinicalNoteGeneratorPort(raw_text="hello world")
        facade = _facade(generator=generator)

        chunks = [chunk async for chunk in facade.stream_generate_note(_encounter())]

        assert "".join(c.delta for c in chunks) == "hello world"

    async def test_render_note_delegates_to_the_renderer(self) -> None:
        from app.modules.clinical_note_ai.domain.enums import ClinicalNoteOutputFormat

        facade = _facade()
        note = make_clinical_note()

        rendered = await facade.render_note(note, target_format=ClinicalNoteOutputFormat.TEXT)

        assert "CHIEF COMPLAINT:" in rendered

    async def test_validate_input_delegates_to_the_use_case(self) -> None:
        facade = _facade()

        result = await facade.validate_input(_encounter())

        assert result.is_valid is True
