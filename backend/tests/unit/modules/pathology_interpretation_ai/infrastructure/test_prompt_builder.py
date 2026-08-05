"""Unit tests for `DefaultPathologyPromptBuilder`."""

from uuid import uuid4

from app.modules.ai.public.dto import AIMessageRole
from app.modules.pathology_interpretation_ai.domain.enums import (
    PathologyExaminationType,
    PathologySetting,
)
from app.modules.pathology_interpretation_ai.domain.value_objects import (
    PathologyInterpretationInput,
    PathologyInterpretationTemplateSet,
)
from app.modules.pathology_interpretation_ai.infrastructure.prompts.prompt_builder import (
    DefaultPathologyPromptBuilder,
)
from tests.unit.modules.pathology_interpretation_ai.application.fakes import FakeAIGateway


def _input(**overrides: object) -> PathologyInterpretationInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "report_text": "Sections show benign glandular tissue with reactive changes noted.",
        "examination_type": PathologyExaminationType.HISTOPATHOLOGY,
        "pathology_setting": PathologySetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return PathologyInterpretationInput(**defaults)  # type: ignore[arg-type]


_TEMPLATE_SET = PathologyInterpretationTemplateSet(
    system_template_name="pathology_interpretation.outpatient.system",
    developer_template_name="pathology_interpretation.outpatient.developer",
    user_template_name="pathology_interpretation.outpatient.user",
    version=1,
)


class TestBuildVariables:
    def test_uses_default_placeholder_text_for_missing_optional_fields(self) -> None:
        builder = DefaultPathologyPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_input())

        assert variables["patient_age"] == "Not provided."
        assert variables["visit_type"] == "Not provided."
        assert variables["clinical_notes"] == "Not provided."
        assert variables["laboratory_interpretation"] == "Not provided."
        assert variables["radiology_interpretation"] == "Not provided."
        assert variables["medical_reasoning_context"] == "Not provided."

    def test_carries_through_report_text_verbatim(self) -> None:
        builder = DefaultPathologyPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            _input(report_text="Benign glandular tissue, no atypia identified.")
        )

        assert variables["report_text"] == "Benign glandular tissue, no atypia identified."

    def test_formats_examination_type_from_its_enum_value(self) -> None:
        builder = DefaultPathologyPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_input(examination_type=PathologyExaminationType.FNAC))

        assert variables["examination_type"] == "fnac"

    def test_formats_patient_sex_and_pregnancy_status_from_enum_values(self) -> None:
        from app.modules.pathology_interpretation_ai.domain.enums import (
            PatientSex,
            PregnancyStatus,
        )

        builder = DefaultPathologyPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            _input(patient_sex=PatientSex.FEMALE, pregnancy_status=PregnancyStatus.PREGNANT)
        )

        assert variables["patient_sex"] == "female"
        assert variables["pregnancy_status"] == "pregnant"

    def test_joins_clinical_notes_with_commas(self) -> None:
        builder = DefaultPathologyPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_input(clinical_notes=("Note A", "Note B")))

        assert variables["clinical_notes"] == "Note A, Note B"

    def test_carries_through_laboratory_radiology_and_medical_reasoning_context(self) -> None:
        builder = DefaultPathologyPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            _input(
                laboratory_interpretation="CA-125 elevated.",
                radiology_interpretation="Adnexal mass on ultrasound.",
                medical_reasoning_context="High suspicion of malignancy.",
            )
        )

        assert variables["laboratory_interpretation"] == "CA-125 elevated."
        assert variables["radiology_interpretation"] == "Adnexal mass on ultrasound."
        assert variables["medical_reasoning_context"] == "High suspicion of malignancy."

    def test_carries_through_language(self) -> None:
        builder = DefaultPathologyPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_input(language="es"))

        assert variables["language"] == "es"


class TestBuildMessages:
    async def test_renders_three_messages_system_system_user(self) -> None:
        gateway = FakeAIGateway(
            rendered_prompts={
                "pathology_interpretation.outpatient.system": "system text",
                "pathology_interpretation.outpatient.developer": "developer text",
                "pathology_interpretation.outpatient.user": "user text",
            }
        )
        builder = DefaultPathologyPromptBuilder(ai_gateway=gateway)

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
        builder = DefaultPathologyPromptBuilder(ai_gateway=gateway)
        template_set = PathologyInterpretationTemplateSet(
            system_template_name="pathology_interpretation.oncology.system",
            developer_template_name="pathology_interpretation.oncology.developer",
            user_template_name="pathology_interpretation.oncology.user",
            version=7,
        )

        await builder.build_messages(_input(), template_set)

        assert gateway.rendered_calls == [
            ("pathology_interpretation.oncology.system", 7),
            ("pathology_interpretation.oncology.developer", 7),
            ("pathology_interpretation.oncology.user", 7),
        ]
