"""Unit tests for `DefaultPromptBuilder`."""

from uuid import uuid4

from app.modules.ai.public.dto import AIMessageRole
from app.modules.clinical_note_ai.domain.enums import NoteStyle
from app.modules.clinical_note_ai.domain.value_objects import (
    ClinicalEncounterInput,
    ClinicalNoteTemplateSet,
)
from app.modules.clinical_note_ai.infrastructure.prompts.prompt_builder import DefaultPromptBuilder
from tests.unit.modules.clinical_note_ai.application.fakes import FakeAIGateway


def _encounter(**overrides: object) -> ClinicalEncounterInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Headache",
        "note_style": NoteStyle.CONCISE,
    }
    defaults.update(overrides)
    return ClinicalEncounterInput(**defaults)  # type: ignore[arg-type]


_TEMPLATE_SET = ClinicalNoteTemplateSet(
    system_template_name="clinical_note.concise.system",
    developer_template_name="clinical_note.concise.developer",
    user_template_name="clinical_note.concise.user",
    version=1,
)


class TestBuildVariables:
    def test_uses_default_placeholder_text_for_missing_optional_fields(self) -> None:
        builder = DefaultPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_encounter())

        assert variables["history_of_present_illness"] == "Not provided."
        assert variables["symptoms"] == "Not provided."

    def test_carries_through_the_chief_complaint_verbatim(self) -> None:
        builder = DefaultPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_encounter(chief_complaint="Chest pain"))

        assert variables["chief_complaint"] == "Chest pain"

    def test_joins_symptoms_with_commas(self) -> None:
        builder = DefaultPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_encounter(symptoms=("nausea", "photophobia")))

        assert variables["symptoms"] == "nausea, photophobia"

    def test_formats_vitals_as_key_value_pairs(self) -> None:
        builder = DefaultPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_encounter(vitals={"BP": "120/80", "HR": "72"}))

        assert variables["vitals"] == "BP: 120/80, HR: 72"

    def test_carries_through_language(self) -> None:
        builder = DefaultPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_encounter(language="es"))

        assert variables["language"] == "es"


class TestBuildMessages:
    async def test_renders_three_messages_system_system_user(self) -> None:
        gateway = FakeAIGateway(
            rendered_prompts={
                "clinical_note.concise.system": "system text",
                "clinical_note.concise.developer": "developer text",
                "clinical_note.concise.user": "user text",
            }
        )
        builder = DefaultPromptBuilder(ai_gateway=gateway)

        messages = await builder.build_messages(_encounter(), _TEMPLATE_SET)

        assert len(messages) == 3
        assert messages[0].role is AIMessageRole.SYSTEM
        assert messages[0].content == "system text"
        assert messages[1].role is AIMessageRole.SYSTEM
        assert messages[1].content == "developer text"
        assert messages[2].role is AIMessageRole.USER
        assert messages[2].content == "user text"

    async def test_renders_using_the_pinned_template_version(self) -> None:
        gateway = FakeAIGateway()
        builder = DefaultPromptBuilder(ai_gateway=gateway)
        template_set = ClinicalNoteTemplateSet(
            system_template_name="clinical_note.detailed.system",
            developer_template_name="clinical_note.detailed.developer",
            user_template_name="clinical_note.detailed.user",
            version=7,
        )

        await builder.build_messages(_encounter(), template_set)

        assert gateway.rendered_calls == [
            ("clinical_note.detailed.system", 7),
            ("clinical_note.detailed.developer", 7),
            ("clinical_note.detailed.user", 7),
        ]
