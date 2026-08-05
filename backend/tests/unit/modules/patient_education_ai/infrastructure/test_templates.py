"""Unit tests for `infrastructure/prompts/templates.py`."""

from app.modules.patient_education_ai.domain.enums import PatientEducationSetting
from app.modules.patient_education_ai.infrastructure.prompts.templates import (
    build_all_templates,
    developer_template_name,
    system_template_name,
    user_template_name,
)


class TestTemplateNames:
    def test_are_prefixed_patient_education(self) -> None:
        assert system_template_name(PatientEducationSetting.ADULT) == (
            "patient_education.adult.system"
        )
        assert developer_template_name(PatientEducationSetting.EMERGENCY_DISCHARGE) == (
            "patient_education.emergency_discharge.developer"
        )
        assert user_template_name(PatientEducationSetting.HOSPITAL_DISCHARGE) == (
            "patient_education.hospital_discharge.user"
        )


class TestBuildAllTemplates:
    def test_builds_eighteen_templates(self) -> None:
        templates = build_all_templates()
        assert len(templates) == 18

    def test_builds_a_triple_for_every_setting(self) -> None:
        templates = build_all_templates()
        names = {template.name for template in templates}
        for setting in PatientEducationSetting:
            assert system_template_name(setting) in names
            assert developer_template_name(setting) in names
            assert user_template_name(setting) in names

    def test_uses_the_given_version(self) -> None:
        templates = build_all_templates(version=7)
        assert all(template.version == 7 for template in templates)

    def test_user_template_variables_include_diagnoses_and_medications(self) -> None:
        templates = build_all_templates()
        user_template = next(
            t
            for t in templates
            if t.name == user_template_name(PatientEducationSetting.HOSPITAL_DISCHARGE)
        )
        assert "diagnoses" in user_template.variable_names
        assert "current_medications" in user_template.variable_names
        assert "prescription_ai_output" in user_template.variable_names
        assert "drug_interaction_ai_output" in user_template.variable_names
        assert "risk_stratification_ai_output" in user_template.variable_names
        assert "laboratory_interpretation" in user_template.variable_names
        assert "radiology_interpretation" in user_template.variable_names
        assert "pathology_interpretation" in user_template.variable_names
        assert "medical_reasoning_context" in user_template.variable_names
        assert "differential_diagnosis_context" in user_template.variable_names
