"""Unit tests for `infrastructure/prompts/templates.py`."""

from app.modules.drug_interaction_ai.domain.enums import DrugInteractionSetting
from app.modules.drug_interaction_ai.infrastructure.prompts.templates import (
    build_all_templates,
    developer_template_name,
    system_template_name,
    user_template_name,
)


class TestTemplateNames:
    def test_are_prefixed_drug_interaction(self) -> None:
        assert system_template_name(DrugInteractionSetting.OUTPATIENT) == (
            "drug_interaction.outpatient.system"
        )
        assert developer_template_name(DrugInteractionSetting.EMERGENCY) == (
            "drug_interaction.emergency.developer"
        )
        assert user_template_name(DrugInteractionSetting.PREGNANCY) == (
            "drug_interaction.pregnancy.user"
        )


class TestBuildAllTemplates:
    def test_builds_twenty_one_templates(self) -> None:
        templates = build_all_templates()
        assert len(templates) == 21

    def test_builds_a_triple_for_every_setting(self) -> None:
        templates = build_all_templates()
        names = {template.name for template in templates}
        for setting in DrugInteractionSetting:
            assert system_template_name(setting) in names
            assert developer_template_name(setting) in names
            assert user_template_name(setting) in names

    def test_uses_the_given_version(self) -> None:
        templates = build_all_templates(version=7)
        assert all(template.version == 7 for template in templates)

    def test_user_template_variables_include_current_medications_and_new_prescription(
        self,
    ) -> None:
        templates = build_all_templates()
        user_template = next(
            t for t in templates if t.name == user_template_name(DrugInteractionSetting.ICU)
        )
        assert "current_medications" in user_template.variable_names
        assert "new_prescription" in user_template.variable_names
        assert "renal_function" in user_template.variable_names
        assert "hepatic_function" in user_template.variable_names
