"""Unit tests for `DefaultReasoningPromptBuilder`."""

from uuid import uuid4

from app.modules.ai.public.dto import AIMessageRole
from app.modules.medical_reasoning_ai.domain.enums import (
    PatientSex,
    PregnancyStatus,
    ReasoningSetting,
)
from app.modules.medical_reasoning_ai.domain.value_objects import (
    MedicalReasoningInput,
    MedicalReasoningTemplateSet,
)
from app.modules.medical_reasoning_ai.infrastructure.prompts.prompt_builder import (
    DefaultReasoningPromptBuilder,
)
from tests.unit.modules.medical_reasoning_ai.application.fakes import FakeAIGateway


def _evidence(**overrides: object) -> MedicalReasoningInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Chest pain",
        "reasoning_setting": ReasoningSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return MedicalReasoningInput(**defaults)  # type: ignore[arg-type]


_TEMPLATE_SET = MedicalReasoningTemplateSet(
    system_template_name="medical_reasoning.outpatient.system",
    developer_template_name="medical_reasoning.outpatient.developer",
    user_template_name="medical_reasoning.outpatient.user",
    version=1,
)


class TestBuildVariables:
    def test_uses_default_placeholder_text_for_missing_optional_fields(self) -> None:
        builder = DefaultReasoningPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_evidence())

        assert variables["history_of_present_illness"] == "Not provided."
        assert variables["symptoms"] == "Not provided."
        assert variables["patient_age"] == "Not provided."
        assert variables["clinical_notes"] == "Not provided."
        assert variables["differential_diagnoses"] == "Not provided."

    def test_carries_through_the_chief_complaint_verbatim(self) -> None:
        builder = DefaultReasoningPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_evidence(chief_complaint="Chest pain"))

        assert variables["chief_complaint"] == "Chest pain"

    def test_formats_patient_sex_from_its_enum_value(self) -> None:
        builder = DefaultReasoningPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_evidence(patient_sex=PatientSex.FEMALE))

        assert variables["patient_sex"] == "female"

    def test_formats_pregnancy_status_from_its_enum_value(self) -> None:
        builder = DefaultReasoningPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_evidence(pregnancy_status=PregnancyStatus.PREGNANT))

        assert variables["pregnancy_status"] == "pregnant"

    def test_joins_clinical_notes_with_commas(self) -> None:
        builder = DefaultReasoningPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_evidence(clinical_notes=("Note A", "Note B")))

        assert variables["clinical_notes"] == "Note A, Note B"

    def test_formats_vitals_as_key_value_pairs(self) -> None:
        builder = DefaultReasoningPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_evidence(vitals={"HR": "110", "BP": "120/80"}))

        assert variables["vitals"] == "HR: 110, BP: 120/80"

    def test_carries_through_language(self) -> None:
        builder = DefaultReasoningPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_evidence(language="es"))

        assert variables["language"] == "es"


class TestBuildMessages:
    async def test_renders_three_messages_system_system_user(self) -> None:
        gateway = FakeAIGateway(
            rendered_prompts={
                "medical_reasoning.outpatient.system": "system text",
                "medical_reasoning.outpatient.developer": "developer text",
                "medical_reasoning.outpatient.user": "user text",
            }
        )
        builder = DefaultReasoningPromptBuilder(ai_gateway=gateway)

        messages = await builder.build_messages(_evidence(), _TEMPLATE_SET)

        assert len(messages) == 3
        assert messages[0].role is AIMessageRole.SYSTEM
        assert messages[0].content == "system text"
        assert messages[1].role is AIMessageRole.SYSTEM
        assert messages[1].content == "developer text"
        assert messages[2].role is AIMessageRole.USER
        assert messages[2].content == "user text"

    async def test_renders_using_the_pinned_template_version(self) -> None:
        gateway = FakeAIGateway()
        builder = DefaultReasoningPromptBuilder(ai_gateway=gateway)
        template_set = MedicalReasoningTemplateSet(
            system_template_name="medical_reasoning.pediatric.system",
            developer_template_name="medical_reasoning.pediatric.developer",
            user_template_name="medical_reasoning.pediatric.user",
            version=7,
        )

        await builder.build_messages(_evidence(), template_set)

        assert gateway.rendered_calls == [
            ("medical_reasoning.pediatric.system", 7),
            ("medical_reasoning.pediatric.developer", 7),
            ("medical_reasoning.pediatric.user", 7),
        ]
