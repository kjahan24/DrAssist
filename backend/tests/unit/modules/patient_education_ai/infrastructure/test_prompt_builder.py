"""Unit tests for `DefaultPatientEducationAnalysisPromptBuilder`."""

from app.modules.ai.public.dto import AIMessageRole
from app.modules.patient_education_ai.domain.value_objects import PatientEducationTemplateSet
from app.modules.patient_education_ai.infrastructure.prompts.prompt_builder import (
    DefaultPatientEducationAnalysisPromptBuilder,
)
from tests.unit.modules.patient_education_ai.application.fakes import FakeAIGateway, make_input

_TEMPLATE_SET = PatientEducationTemplateSet(
    system_template_name="patient_education.adult.system",
    developer_template_name="patient_education.adult.developer",
    user_template_name="patient_education.adult.user",
    version=1,
)


class TestBuildVariables:
    def test_uses_default_placeholder_text_for_missing_optional_fields(self) -> None:
        builder = DefaultPatientEducationAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(make_input())

        assert variables["patient_age"] == "Not provided."
        assert variables["prescription_ai_output"] == "Not provided."
        assert variables["drug_interaction_ai_output"] == "Not provided."
        assert variables["risk_stratification_ai_output"] == "Not provided."
        assert variables["laboratory_interpretation"] == "Not provided."
        assert variables["radiology_interpretation"] == "Not provided."
        assert variables["pathology_interpretation"] == "Not provided."
        assert variables["medical_reasoning_context"] == "Not provided."
        assert variables["differential_diagnosis_context"] == "Not provided."

    def test_joins_diagnoses_and_current_medications_with_commas(self) -> None:
        builder = DefaultPatientEducationAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            make_input(
                diagnoses=("Hypertension", "Diabetes"),
                current_medications=("Lisinopril", "Metformin"),
            )
        )

        assert variables["diagnoses"] == "Hypertension, Diabetes"
        assert variables["current_medications"] == "Lisinopril, Metformin"

    def test_carries_through_language(self) -> None:
        builder = DefaultPatientEducationAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(make_input(language="es"))

        assert variables["language"] == "es"

    def test_formats_patient_age(self) -> None:
        builder = DefaultPatientEducationAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(make_input(patient_age=67))

        assert variables["patient_age"] == "67"

    def test_carries_through_peer_module_output_text(self) -> None:
        builder = DefaultPatientEducationAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            make_input(
                prescription_ai_output="Lisinopril 10mg daily.",
                drug_interaction_ai_output="No major interactions found.",
                risk_stratification_ai_output="Low risk.",
                laboratory_interpretation="Normal renal function.",
                radiology_interpretation="No acute findings.",
                pathology_interpretation="Benign.",
                medical_reasoning_context="Working diagnosis: hypertension.",
                differential_diagnosis_context="Primary hypertension most likely.",
            )
        )

        assert variables["prescription_ai_output"] == "Lisinopril 10mg daily."
        assert variables["drug_interaction_ai_output"] == "No major interactions found."
        assert variables["risk_stratification_ai_output"] == "Low risk."
        assert variables["laboratory_interpretation"] == "Normal renal function."
        assert variables["radiology_interpretation"] == "No acute findings."
        assert variables["pathology_interpretation"] == "Benign."
        assert variables["medical_reasoning_context"] == "Working diagnosis: hypertension."
        assert variables["differential_diagnosis_context"] == "Primary hypertension most likely."

    def test_joins_clinical_notes_and_soap_notes(self) -> None:
        builder = DefaultPatientEducationAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            make_input(
                clinical_notes=("Patient reports fatigue.",),
                soap_notes=("S: fatigue. O: BP 150/95.",),
            )
        )

        assert variables["clinical_notes"] == "Patient reports fatigue."
        assert variables["soap_notes"] == "S: fatigue. O: BP 150/95."


class TestBuildMessages:
    async def test_renders_three_messages_system_system_user(self) -> None:
        gateway = FakeAIGateway(
            rendered_prompts={
                "patient_education.adult.system": "system text",
                "patient_education.adult.developer": "developer text",
                "patient_education.adult.user": "user text",
            }
        )
        builder = DefaultPatientEducationAnalysisPromptBuilder(ai_gateway=gateway)

        messages = await builder.build_messages(make_input(), _TEMPLATE_SET)

        assert len(messages) == 3
        assert messages[0].role is AIMessageRole.SYSTEM
        assert messages[0].content == "system text"
        assert messages[1].role is AIMessageRole.SYSTEM
        assert messages[1].content == "developer text"
        assert messages[2].role is AIMessageRole.USER
        assert messages[2].content == "user text"

    async def test_renders_using_the_pinned_template_version(self) -> None:
        gateway = FakeAIGateway()
        builder = DefaultPatientEducationAnalysisPromptBuilder(ai_gateway=gateway)
        template_set = PatientEducationTemplateSet(
            system_template_name="patient_education.geriatric.system",
            developer_template_name="patient_education.geriatric.developer",
            user_template_name="patient_education.geriatric.user",
            version=7,
        )

        await builder.build_messages(make_input(), template_set)

        assert gateway.rendered_calls == [
            ("patient_education.geriatric.system", 7),
            ("patient_education.geriatric.developer", 7),
            ("patient_education.geriatric.user", 7),
        ]
