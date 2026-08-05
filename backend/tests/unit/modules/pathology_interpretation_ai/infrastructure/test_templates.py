"""Unit tests for `infrastructure/prompts/templates.py`."""

from app.modules.pathology_interpretation_ai.domain.enums import PathologySetting
from app.modules.pathology_interpretation_ai.infrastructure.prompts.templates import (
    build_all_templates,
    developer_template_name,
    system_template_name,
    user_template_name,
)


class TestTemplateNames:
    def test_are_prefixed_pathology_interpretation(self) -> None:
        assert system_template_name(PathologySetting.OUTPATIENT) == (
            "pathology_interpretation.outpatient.system"
        )
        assert developer_template_name(PathologySetting.EMERGENCY) == (
            "pathology_interpretation.emergency.developer"
        )
        assert user_template_name(PathologySetting.ONCOLOGY) == (
            "pathology_interpretation.oncology.user"
        )


class TestBuildAllTemplates:
    def test_builds_fifteen_templates(self) -> None:
        templates = build_all_templates()
        assert len(templates) == 15

    def test_builds_a_triple_for_every_setting(self) -> None:
        templates = build_all_templates()
        names = {template.name for template in templates}
        for setting in PathologySetting:
            assert system_template_name(setting) in names
            assert developer_template_name(setting) in names
            assert user_template_name(setting) in names

    def test_uses_the_given_version(self) -> None:
        templates = build_all_templates(version=7)
        assert all(template.version == 7 for template in templates)

    def test_user_template_variables_include_report_text_and_examination_type(self) -> None:
        templates = build_all_templates()
        user_template = next(
            t for t in templates if t.name == user_template_name(PathologySetting.INPATIENT)
        )
        assert "report_text" in user_template.variable_names
        assert "examination_type" in user_template.variable_names
        assert "radiology_interpretation" in user_template.variable_names
