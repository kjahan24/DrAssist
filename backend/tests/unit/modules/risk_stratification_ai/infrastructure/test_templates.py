"""Unit tests for `infrastructure/prompts/templates.py`."""

from app.modules.risk_stratification_ai.domain.enums import RiskStratificationSetting
from app.modules.risk_stratification_ai.infrastructure.prompts.templates import (
    build_all_templates,
    developer_template_name,
    system_template_name,
    user_template_name,
)


class TestTemplateNames:
    def test_are_prefixed_risk_stratification(self) -> None:
        assert system_template_name(RiskStratificationSetting.OUTPATIENT) == (
            "risk_stratification.outpatient.system"
        )
        assert developer_template_name(RiskStratificationSetting.EMERGENCY) == (
            "risk_stratification.emergency.developer"
        )
        assert user_template_name(RiskStratificationSetting.ICU) == ("risk_stratification.icu.user")


class TestBuildAllTemplates:
    def test_builds_eighteen_templates(self) -> None:
        templates = build_all_templates()
        assert len(templates) == 18

    def test_builds_a_triple_for_every_setting(self) -> None:
        templates = build_all_templates()
        names = {template.name for template in templates}
        for setting in RiskStratificationSetting:
            assert system_template_name(setting) in names
            assert developer_template_name(setting) in names
            assert user_template_name(setting) in names

    def test_uses_the_given_version(self) -> None:
        templates = build_all_templates(version=7)
        assert all(template.version == 7 for template in templates)

    def test_user_template_variables_include_vital_signs_and_lab_values(self) -> None:
        templates = build_all_templates()
        user_template = next(
            t for t in templates if t.name == user_template_name(RiskStratificationSetting.ICU)
        )
        assert "vital_signs" in user_template.variable_names
        assert "lab_values" in user_template.variable_names
        assert "laboratory_interpretation" in user_template.variable_names
        assert "radiology_interpretation" in user_template.variable_names
        assert "pathology_interpretation" in user_template.variable_names
        assert "medical_reasoning_context" in user_template.variable_names
