"""Unit tests for `DefaultDifferentialDiagnosisPromptBuilder`."""

from uuid import uuid4

from app.modules.ai.public.dto import AIMessageRole
from app.modules.differential_diagnosis_ai.domain.enums import (
    ClinicalSetting,
    PatientSex,
    PregnancyStatus,
)
from app.modules.differential_diagnosis_ai.domain.value_objects import (
    DifferentialDiagnosisInput,
    DifferentialDiagnosisTemplateSet,
)
from app.modules.differential_diagnosis_ai.infrastructure.prompts.prompt_builder import (
    DefaultDifferentialDiagnosisPromptBuilder,
)
from tests.unit.modules.differential_diagnosis_ai.application.fakes import FakeAIGateway


def _evidence(**overrides: object) -> DifferentialDiagnosisInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Chest pain",
        "clinical_setting": ClinicalSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return DifferentialDiagnosisInput(**defaults)  # type: ignore[arg-type]


_TEMPLATE_SET = DifferentialDiagnosisTemplateSet(
    system_template_name="differential_diagnosis_suggestion.outpatient.system",
    developer_template_name="differential_diagnosis_suggestion.outpatient.developer",
    user_template_name="differential_diagnosis_suggestion.outpatient.user",
    version=1,
)


class TestBuildVariables:
    def test_uses_default_placeholder_text_for_missing_optional_fields(self) -> None:
        builder = DefaultDifferentialDiagnosisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_evidence())

        assert variables["history_of_present_illness"] == "Not provided."
        assert variables["symptoms"] == "Not provided."
        assert variables["patient_age"] == "Not provided."
        assert variables["pregnancy_status"] == "Not provided."
        assert variables["imaging_summary"] == "Not provided."
        assert variables["icd10_suggestions"] == "Not provided."
        assert variables["prescription_suggestions"] == "Not provided."

    def test_carries_through_the_chief_complaint_verbatim(self) -> None:
        builder = DefaultDifferentialDiagnosisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_evidence(chief_complaint="Chest pain"))

        assert variables["chief_complaint"] == "Chest pain"

    def test_formats_patient_age_as_a_string(self) -> None:
        builder = DefaultDifferentialDiagnosisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_evidence(patient_age=54))

        assert variables["patient_age"] == "54"

    def test_formats_patient_sex_from_its_enum_value(self) -> None:
        builder = DefaultDifferentialDiagnosisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_evidence(patient_sex=PatientSex.FEMALE))

        assert variables["patient_sex"] == "female"

    def test_formats_pregnancy_status_from_its_enum_value(self) -> None:
        builder = DefaultDifferentialDiagnosisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_evidence(pregnancy_status=PregnancyStatus.PREGNANT))

        assert variables["pregnancy_status"] == "pregnant"

    def test_joins_laboratory_results_with_commas(self) -> None:
        builder = DefaultDifferentialDiagnosisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            _evidence(laboratory_results=("Troponin: 0.02", "WBC: 11.2"))
        )

        assert variables["laboratory_results"] == "Troponin: 0.02, WBC: 11.2"

    def test_formats_vitals_as_key_value_pairs(self) -> None:
        builder = DefaultDifferentialDiagnosisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_evidence(vitals={"HR": "110", "BP": "120/80"}))

        assert variables["vitals"] == "HR: 110, BP: 120/80"

    def test_carries_through_language(self) -> None:
        builder = DefaultDifferentialDiagnosisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_evidence(language="es"))

        assert variables["language"] == "es"


class TestBuildMessages:
    async def test_renders_three_messages_system_system_user(self) -> None:
        gateway = FakeAIGateway(
            rendered_prompts={
                "differential_diagnosis_suggestion.outpatient.system": "system text",
                "differential_diagnosis_suggestion.outpatient.developer": "developer text",
                "differential_diagnosis_suggestion.outpatient.user": "user text",
            }
        )
        builder = DefaultDifferentialDiagnosisPromptBuilder(ai_gateway=gateway)

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
        builder = DefaultDifferentialDiagnosisPromptBuilder(ai_gateway=gateway)
        template_set = DifferentialDiagnosisTemplateSet(
            system_template_name="differential_diagnosis_suggestion.pediatric.system",
            developer_template_name="differential_diagnosis_suggestion.pediatric.developer",
            user_template_name="differential_diagnosis_suggestion.pediatric.user",
            version=7,
        )

        await builder.build_messages(_evidence(), template_set)

        assert gateway.rendered_calls == [
            ("differential_diagnosis_suggestion.pediatric.system", 7),
            ("differential_diagnosis_suggestion.pediatric.developer", 7),
            ("differential_diagnosis_suggestion.pediatric.user", 7),
        ]
