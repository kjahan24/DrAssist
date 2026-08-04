"""Unit tests for `DefaultICD10PromptBuilder`."""

from uuid import uuid4

from app.modules.ai.public.dto import AIMessageRole
from app.modules.icd10_ai.domain.enums import CodingSetting, PatientSex
from app.modules.icd10_ai.domain.value_objects import ICD10CodingInput, ICD10TemplateSet
from app.modules.icd10_ai.infrastructure.prompts.prompt_builder import DefaultICD10PromptBuilder
from tests.unit.modules.icd10_ai.application.fakes import FakeAIGateway


def _coding_input(**overrides: object) -> ICD10CodingInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Sore throat",
        "coding_setting": CodingSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return ICD10CodingInput(**defaults)  # type: ignore[arg-type]


_TEMPLATE_SET = ICD10TemplateSet(
    system_template_name="icd10_suggestion.outpatient.system",
    developer_template_name="icd10_suggestion.outpatient.developer",
    user_template_name="icd10_suggestion.outpatient.user",
    version=1,
)


class TestBuildVariables:
    def test_uses_default_placeholder_text_for_missing_optional_fields(self) -> None:
        builder = DefaultICD10PromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_coding_input())

        assert variables["history_of_present_illness"] == "Not provided."
        assert variables["symptoms"] == "Not provided."
        assert variables["patient_age"] == "Not provided."
        assert variables["patient_sex"] == "Not provided."
        assert variables["existing_diagnoses"] == "Not provided."

    def test_carries_through_the_chief_complaint_verbatim(self) -> None:
        builder = DefaultICD10PromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_coding_input(chief_complaint="Chest pain"))

        assert variables["chief_complaint"] == "Chest pain"

    def test_formats_patient_age_as_a_string(self) -> None:
        builder = DefaultICD10PromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_coding_input(patient_age=34))

        assert variables["patient_age"] == "34"

    def test_formats_patient_sex_from_its_enum_value(self) -> None:
        builder = DefaultICD10PromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_coding_input(patient_sex=PatientSex.FEMALE))

        assert variables["patient_sex"] == "female"

    def test_joins_existing_diagnoses_with_commas(self) -> None:
        builder = DefaultICD10PromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            _coding_input(existing_diagnoses=("asthma", "hypertension"))
        )

        assert variables["existing_diagnoses"] == "asthma, hypertension"

    def test_carries_through_language(self) -> None:
        builder = DefaultICD10PromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_coding_input(language="es"))

        assert variables["language"] == "es"


class TestBuildMessages:
    async def test_renders_three_messages_system_system_user(self) -> None:
        gateway = FakeAIGateway(
            rendered_prompts={
                "icd10_suggestion.outpatient.system": "system text",
                "icd10_suggestion.outpatient.developer": "developer text",
                "icd10_suggestion.outpatient.user": "user text",
            }
        )
        builder = DefaultICD10PromptBuilder(ai_gateway=gateway)

        messages = await builder.build_messages(_coding_input(), _TEMPLATE_SET)

        assert len(messages) == 3
        assert messages[0].role is AIMessageRole.SYSTEM
        assert messages[0].content == "system text"
        assert messages[1].role is AIMessageRole.SYSTEM
        assert messages[1].content == "developer text"
        assert messages[2].role is AIMessageRole.USER
        assert messages[2].content == "user text"

    async def test_renders_using_the_pinned_template_version(self) -> None:
        gateway = FakeAIGateway()
        builder = DefaultICD10PromptBuilder(ai_gateway=gateway)
        template_set = ICD10TemplateSet(
            system_template_name="icd10_suggestion.emergency.system",
            developer_template_name="icd10_suggestion.emergency.developer",
            user_template_name="icd10_suggestion.emergency.user",
            version=7,
        )

        await builder.build_messages(_coding_input(), template_set)

        assert gateway.rendered_calls == [
            ("icd10_suggestion.emergency.system", 7),
            ("icd10_suggestion.emergency.developer", 7),
            ("icd10_suggestion.emergency.user", 7),
        ]
