"""Unit tests for `DefaultPrescriptionPromptBuilder`."""

from uuid import uuid4

from app.modules.ai.public.dto import AIMessageRole
from app.modules.prescription_ai.domain.enums import (
    PatientSex,
    PregnancyStatus,
    PrescribingSetting,
)
from app.modules.prescription_ai.domain.value_objects import (
    PrescriptionContextInput,
    PrescriptionTemplateSet,
)
from app.modules.prescription_ai.infrastructure.prompts.prompt_builder import (
    DefaultPrescriptionPromptBuilder,
)
from tests.unit.modules.prescription_ai.application.fakes import FakeAIGateway


def _context(**overrides: object) -> PrescriptionContextInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Sore throat",
        "prescribing_setting": PrescribingSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return PrescriptionContextInput(**defaults)  # type: ignore[arg-type]


_TEMPLATE_SET = PrescriptionTemplateSet(
    system_template_name="prescription_suggestion.outpatient.system",
    developer_template_name="prescription_suggestion.outpatient.developer",
    user_template_name="prescription_suggestion.outpatient.user",
    version=1,
)


class TestBuildVariables:
    def test_uses_default_placeholder_text_for_missing_optional_fields(self) -> None:
        builder = DefaultPrescriptionPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_context())

        assert variables["history_of_present_illness"] == "Not provided."
        assert variables["symptoms"] == "Not provided."
        assert variables["patient_age"] == "Not provided."
        assert variables["patient_sex"] == "Not provided."
        assert variables["pregnancy_status"] == "Not provided."
        assert variables["weight_kg"] == "Not provided."
        assert variables["existing_medications"] == "Not provided."

    def test_carries_through_the_chief_complaint_verbatim(self) -> None:
        builder = DefaultPrescriptionPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_context(chief_complaint="Chest pain"))

        assert variables["chief_complaint"] == "Chest pain"

    def test_formats_patient_age_as_a_string(self) -> None:
        builder = DefaultPrescriptionPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_context(patient_age=34))

        assert variables["patient_age"] == "34"

    def test_formats_patient_sex_from_its_enum_value(self) -> None:
        builder = DefaultPrescriptionPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_context(patient_sex=PatientSex.FEMALE))

        assert variables["patient_sex"] == "female"

    def test_formats_pregnancy_status_from_its_enum_value(self) -> None:
        builder = DefaultPrescriptionPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_context(pregnancy_status=PregnancyStatus.PREGNANT))

        assert variables["pregnancy_status"] == "pregnant"

    def test_formats_weight_as_a_string(self) -> None:
        builder = DefaultPrescriptionPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_context(weight_kg=68.5))

        assert variables["weight_kg"] == "68.5"

    def test_joins_existing_medications_with_commas(self) -> None:
        builder = DefaultPrescriptionPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            _context(existing_medications=("lisinopril", "metformin"))
        )

        assert variables["existing_medications"] == "lisinopril, metformin"

    def test_formats_vitals_as_key_value_pairs(self) -> None:
        builder = DefaultPrescriptionPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_context(vitals={"BP": "120/80", "HR": "72"}))

        assert variables["vitals"] == "BP: 120/80, HR: 72"

    def test_carries_through_language(self) -> None:
        builder = DefaultPrescriptionPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_context(language="es"))

        assert variables["language"] == "es"


class TestBuildMessages:
    async def test_renders_three_messages_system_system_user(self) -> None:
        gateway = FakeAIGateway(
            rendered_prompts={
                "prescription_suggestion.outpatient.system": "system text",
                "prescription_suggestion.outpatient.developer": "developer text",
                "prescription_suggestion.outpatient.user": "user text",
            }
        )
        builder = DefaultPrescriptionPromptBuilder(ai_gateway=gateway)

        messages = await builder.build_messages(_context(), _TEMPLATE_SET)

        assert len(messages) == 3
        assert messages[0].role is AIMessageRole.SYSTEM
        assert messages[0].content == "system text"
        assert messages[1].role is AIMessageRole.SYSTEM
        assert messages[1].content == "developer text"
        assert messages[2].role is AIMessageRole.USER
        assert messages[2].content == "user text"

    async def test_renders_using_the_pinned_template_version(self) -> None:
        gateway = FakeAIGateway()
        builder = DefaultPrescriptionPromptBuilder(ai_gateway=gateway)
        template_set = PrescriptionTemplateSet(
            system_template_name="prescription_suggestion.geriatric.system",
            developer_template_name="prescription_suggestion.geriatric.developer",
            user_template_name="prescription_suggestion.geriatric.user",
            version=7,
        )

        await builder.build_messages(_context(), template_set)

        assert gateway.rendered_calls == [
            ("prescription_suggestion.geriatric.system", 7),
            ("prescription_suggestion.geriatric.developer", 7),
            ("prescription_suggestion.geriatric.user", 7),
        ]
