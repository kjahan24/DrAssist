"""Unit tests for `DefaultRadiologyPromptBuilder`."""

from uuid import uuid4

from app.modules.ai.public.dto import AIMessageRole
from app.modules.radiology_interpretation_ai.domain.enums import (
    RadiologyExaminationType,
    RadiologySetting,
)
from app.modules.radiology_interpretation_ai.domain.value_objects import (
    RadiologyInterpretationInput,
    RadiologyInterpretationTemplateSet,
)
from app.modules.radiology_interpretation_ai.infrastructure.prompts.prompt_builder import (
    DefaultRadiologyPromptBuilder,
)
from tests.unit.modules.radiology_interpretation_ai.application.fakes import FakeAIGateway


def _input(**overrides: object) -> RadiologyInterpretationInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "report_text": "The lungs are clear bilaterally. No acute cardiopulmonary abnormality.",
        "examination_type": RadiologyExaminationType.CHEST_XRAY,
        "radiology_setting": RadiologySetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return RadiologyInterpretationInput(**defaults)  # type: ignore[arg-type]


_TEMPLATE_SET = RadiologyInterpretationTemplateSet(
    system_template_name="radiology_interpretation.outpatient.system",
    developer_template_name="radiology_interpretation.outpatient.developer",
    user_template_name="radiology_interpretation.outpatient.user",
    version=1,
)


class TestBuildVariables:
    def test_uses_default_placeholder_text_for_missing_optional_fields(self) -> None:
        builder = DefaultRadiologyPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_input())

        assert variables["patient_age"] == "Not provided."
        assert variables["visit_type"] == "Not provided."
        assert variables["clinical_notes"] == "Not provided."
        assert variables["laboratory_interpretation"] == "Not provided."
        assert variables["medical_reasoning_context"] == "Not provided."

    def test_carries_through_report_text_verbatim(self) -> None:
        builder = DefaultRadiologyPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            _input(report_text="Clear lungs bilaterally, no acute findings.")
        )

        assert variables["report_text"] == "Clear lungs bilaterally, no acute findings."

    def test_formats_examination_type_from_its_enum_value(self) -> None:
        builder = DefaultRadiologyPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            _input(examination_type=RadiologyExaminationType.CT_BRAIN)
        )

        assert variables["examination_type"] == "ct_brain"

    def test_formats_patient_sex_and_pregnancy_status_from_enum_values(self) -> None:
        from app.modules.radiology_interpretation_ai.domain.enums import (
            PatientSex,
            PregnancyStatus,
        )

        builder = DefaultRadiologyPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            _input(patient_sex=PatientSex.FEMALE, pregnancy_status=PregnancyStatus.PREGNANT)
        )

        assert variables["patient_sex"] == "female"
        assert variables["pregnancy_status"] == "pregnant"

    def test_joins_clinical_notes_with_commas(self) -> None:
        builder = DefaultRadiologyPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_input(clinical_notes=("Note A", "Note B")))

        assert variables["clinical_notes"] == "Note A, Note B"

    def test_carries_through_laboratory_interpretation_and_medical_reasoning_context(self) -> None:
        builder = DefaultRadiologyPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            _input(
                laboratory_interpretation="Potassium critically elevated.",
                medical_reasoning_context="High suspicion of renal failure.",
            )
        )

        assert variables["laboratory_interpretation"] == "Potassium critically elevated."
        assert variables["medical_reasoning_context"] == "High suspicion of renal failure."

    def test_carries_through_language(self) -> None:
        builder = DefaultRadiologyPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_input(language="es"))

        assert variables["language"] == "es"


class TestBuildMessages:
    async def test_renders_three_messages_system_system_user(self) -> None:
        gateway = FakeAIGateway(
            rendered_prompts={
                "radiology_interpretation.outpatient.system": "system text",
                "radiology_interpretation.outpatient.developer": "developer text",
                "radiology_interpretation.outpatient.user": "user text",
            }
        )
        builder = DefaultRadiologyPromptBuilder(ai_gateway=gateway)

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
        builder = DefaultRadiologyPromptBuilder(ai_gateway=gateway)
        template_set = RadiologyInterpretationTemplateSet(
            system_template_name="radiology_interpretation.pediatric.system",
            developer_template_name="radiology_interpretation.pediatric.developer",
            user_template_name="radiology_interpretation.pediatric.user",
            version=7,
        )

        await builder.build_messages(_input(), template_set)

        assert gateway.rendered_calls == [
            ("radiology_interpretation.pediatric.system", 7),
            ("radiology_interpretation.pediatric.developer", 7),
            ("radiology_interpretation.pediatric.user", 7),
        ]
