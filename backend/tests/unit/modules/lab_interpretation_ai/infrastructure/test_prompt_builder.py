"""Unit tests for `DefaultLabPromptBuilder`."""

from uuid import uuid4

from app.modules.ai.public.dto import AIMessageRole
from app.modules.lab_interpretation_ai.domain.enums import LabInterpretationSetting
from app.modules.lab_interpretation_ai.domain.value_objects import (
    LabInterpretationInput,
    LabInterpretationTemplateSet,
)
from app.modules.lab_interpretation_ai.infrastructure.prompts.prompt_builder import (
    DefaultLabPromptBuilder,
)
from tests.unit.modules.lab_interpretation_ai.application.fakes import (
    FakeAIGateway,
    make_lab_value,
)


def _input(**overrides: object) -> LabInterpretationInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "lab_values": (make_lab_value(),),
        "lab_setting": LabInterpretationSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return LabInterpretationInput(**defaults)  # type: ignore[arg-type]


_TEMPLATE_SET = LabInterpretationTemplateSet(
    system_template_name="lab_interpretation.outpatient.system",
    developer_template_name="lab_interpretation.outpatient.developer",
    user_template_name="lab_interpretation.outpatient.user",
    version=1,
)


class TestBuildVariables:
    def test_uses_default_placeholder_text_for_missing_optional_fields(self) -> None:
        builder = DefaultLabPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_input())

        assert variables["patient_age"] == "Not provided."
        assert variables["visit_type"] == "Not provided."
        assert variables["medical_conditions"] == "Not provided."
        assert variables["clinical_notes"] == "Not provided."

    def test_formats_lab_values_with_unit_and_reference_range(self) -> None:
        builder = DefaultLabPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            _input(
                lab_values=(
                    make_lab_value(
                        test_name="Potassium",
                        value="6.8",
                        unit="mmol/L",
                        reference_range="3.5-5.0",
                    ),
                )
            )
        )

        assert variables["lab_values"] == "Potassium 6.8 mmol/L (ref: 3.5-5.0)"

    def test_joins_multiple_lab_values_with_semicolons(self) -> None:
        builder = DefaultLabPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            _input(
                lab_values=(
                    make_lab_value(test_name="Potassium"),
                    make_lab_value(test_name="Sodium", numeric_value=140.0),
                )
            )
        )

        assert "Potassium" in variables["lab_values"]
        assert "Sodium" in variables["lab_values"]
        assert "; " in variables["lab_values"]

    def test_formats_patient_sex_and_pregnancy_status_from_enum_values(self) -> None:
        from app.modules.lab_interpretation_ai.domain.enums import PatientSex, PregnancyStatus

        builder = DefaultLabPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            _input(patient_sex=PatientSex.FEMALE, pregnancy_status=PregnancyStatus.PREGNANT)
        )

        assert variables["patient_sex"] == "female"
        assert variables["pregnancy_status"] == "pregnant"

    def test_carries_through_language(self) -> None:
        builder = DefaultLabPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_input(language="es"))

        assert variables["language"] == "es"


class TestBuildMessages:
    async def test_renders_three_messages_system_system_user(self) -> None:
        gateway = FakeAIGateway(
            rendered_prompts={
                "lab_interpretation.outpatient.system": "system text",
                "lab_interpretation.outpatient.developer": "developer text",
                "lab_interpretation.outpatient.user": "user text",
            }
        )
        builder = DefaultLabPromptBuilder(ai_gateway=gateway)

        messages = await builder.build_messages(_input(), _TEMPLATE_SET)

        assert len(messages) == 3
        assert messages[0].role is AIMessageRole.SYSTEM
        assert messages[0].content == "system text"
        assert messages[1].role is AIMessageRole.SYSTEM
        assert messages[1].content == "developer text"
        assert messages[2].role is AIMessageRole.USER
        assert messages[2].content == "user text"

    async def test_renders_using_the_pinned_template_version(self) -> None:
        gateway = FakeAIGateway()
        builder = DefaultLabPromptBuilder(ai_gateway=gateway)
        template_set = LabInterpretationTemplateSet(
            system_template_name="lab_interpretation.pediatric.system",
            developer_template_name="lab_interpretation.pediatric.developer",
            user_template_name="lab_interpretation.pediatric.user",
            version=7,
        )

        await builder.build_messages(_input(), template_set)

        assert gateway.rendered_calls == [
            ("lab_interpretation.pediatric.system", 7),
            ("lab_interpretation.pediatric.developer", 7),
            ("lab_interpretation.pediatric.user", 7),
        ]
