"""Unit tests for `DefaultSOAPPromptBuilder`."""

from uuid import uuid4

from app.modules.ai.public.dto import AIMessageRole
from app.modules.soap_note_ai.domain.enums import PatientSex, SOAPStyle
from app.modules.soap_note_ai.domain.value_objects import SOAPEncounterInput, SOAPTemplateSet
from app.modules.soap_note_ai.infrastructure.prompts.prompt_builder import DefaultSOAPPromptBuilder
from tests.unit.modules.soap_note_ai.application.fakes import FakeAIGateway


def _encounter(**overrides: object) -> SOAPEncounterInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Headache",
        "soap_style": SOAPStyle.STANDARD,
    }
    defaults.update(overrides)
    return SOAPEncounterInput(**defaults)  # type: ignore[arg-type]


_TEMPLATE_SET = SOAPTemplateSet(
    system_template_name="soap_note.standard.system",
    developer_template_name="soap_note.standard.developer",
    user_template_name="soap_note.standard.user",
    version=1,
)


class TestBuildVariables:
    def test_uses_default_placeholder_text_for_missing_optional_fields(self) -> None:
        builder = DefaultSOAPPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_encounter())

        assert variables["history_of_present_illness"] == "Not provided."
        assert variables["symptoms"] == "Not provided."
        assert variables["patient_age"] == "Not provided."
        assert variables["patient_sex"] == "Not provided."

    def test_carries_through_the_chief_complaint_verbatim(self) -> None:
        builder = DefaultSOAPPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_encounter(chief_complaint="Chest pain"))

        assert variables["chief_complaint"] == "Chest pain"

    def test_formats_patient_age_as_a_string(self) -> None:
        builder = DefaultSOAPPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_encounter(patient_age=34))

        assert variables["patient_age"] == "34"

    def test_formats_patient_sex_from_its_enum_value(self) -> None:
        builder = DefaultSOAPPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_encounter(patient_sex=PatientSex.FEMALE))

        assert variables["patient_sex"] == "female"

    def test_joins_symptoms_with_commas(self) -> None:
        builder = DefaultSOAPPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_encounter(symptoms=("nausea", "photophobia")))

        assert variables["symptoms"] == "nausea, photophobia"

    def test_formats_vitals_as_key_value_pairs(self) -> None:
        builder = DefaultSOAPPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_encounter(vitals={"BP": "120/80", "HR": "72"}))

        assert variables["vitals"] == "BP: 120/80, HR: 72"

    def test_carries_through_language(self) -> None:
        builder = DefaultSOAPPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_encounter(language="es"))

        assert variables["language"] == "es"


class TestBuildMessages:
    async def test_renders_three_messages_system_system_user(self) -> None:
        gateway = FakeAIGateway(
            rendered_prompts={
                "soap_note.standard.system": "system text",
                "soap_note.standard.developer": "developer text",
                "soap_note.standard.user": "user text",
            }
        )
        builder = DefaultSOAPPromptBuilder(ai_gateway=gateway)

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
        builder = DefaultSOAPPromptBuilder(ai_gateway=gateway)
        template_set = SOAPTemplateSet(
            system_template_name="soap_note.detailed.system",
            developer_template_name="soap_note.detailed.developer",
            user_template_name="soap_note.detailed.user",
            version=7,
        )

        await builder.build_messages(_encounter(), template_set)

        assert gateway.rendered_calls == [
            ("soap_note.detailed.system", 7),
            ("soap_note.detailed.developer", 7),
            ("soap_note.detailed.user", 7),
        ]
