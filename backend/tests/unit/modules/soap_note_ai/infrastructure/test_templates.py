"""Unit tests for `infrastructure/prompts/templates.py` — the 15
production prompt templates (5 `SOAPStyle`s x system/developer/user)."""

from app.modules.ai.domain.value_objects import PromptTemplate
from app.modules.soap_note_ai.domain.enums import SOAPStyle
from app.modules.soap_note_ai.infrastructure.prompts.templates import (
    build_all_templates,
    developer_template_name,
    system_template_name,
    user_template_name,
)


class TestTemplateNaming:
    def test_system_template_name_is_style_scoped(self) -> None:
        assert system_template_name(SOAPStyle.CONCISE) == "soap_note.concise.system"

    def test_developer_template_name_is_style_scoped(self) -> None:
        assert developer_template_name(SOAPStyle.EMERGENCY) == "soap_note.emergency.developer"

    def test_user_template_name_is_style_scoped(self) -> None:
        assert user_template_name(SOAPStyle.FOLLOW_UP) == "soap_note.follow_up.user"

    def test_every_soap_style_produces_a_distinct_name_per_slot(self) -> None:
        names = {system_template_name(style) for style in SOAPStyle}
        assert len(names) == len(SOAPStyle)


class TestBuildAllTemplates:
    def test_builds_fifteen_templates(self) -> None:
        templates = build_all_templates()
        assert len(templates) == 15

    def test_every_template_is_a_valid_prompt_template(self) -> None:
        for template in build_all_templates():
            assert isinstance(template, PromptTemplate)

    def test_every_style_has_a_system_developer_and_user_template(self) -> None:
        templates = build_all_templates()
        names = {t.name for t in templates}
        for style in SOAPStyle:
            assert system_template_name(style) in names
            assert developer_template_name(style) in names
            assert user_template_name(style) in names

    def test_all_templates_share_the_requested_version(self) -> None:
        templates = build_all_templates(version=3)
        assert all(t.version == 3 for t in templates)

    def test_system_templates_declare_the_language_variable(self) -> None:
        templates = build_all_templates()
        system_templates = [t for t in templates if t.name.endswith(".system")]
        assert all("language" in t.variable_names for t in system_templates)

    def test_user_templates_declare_the_encounter_variables(self) -> None:
        templates = build_all_templates()
        user_templates = [t for t in templates if t.name.endswith(".user")]
        for template in user_templates:
            assert "chief_complaint" in template.variable_names
            assert "plan" in template.variable_names
            assert "patient_age" in template.variable_names
            assert "patient_sex" in template.variable_names

    def test_developer_templates_carry_the_json_contract(self) -> None:
        templates = build_all_templates()
        developer_templates = [t for t in templates if t.name.endswith(".developer")]
        for template in developer_templates:
            assert "JSON" in template.template_string
            assert "subjective" in template.template_string
            assert "objective" in template.template_string
            assert "assessment" in template.template_string
            assert "plan" in template.template_string

    def test_developer_templates_declare_no_variables(self) -> None:
        templates = build_all_templates()
        developer_templates = [t for t in templates if t.name.endswith(".developer")]
        assert all(t.variable_names == frozenset() for t in developer_templates)

    def test_no_declared_variable_is_missing_from_its_own_template_text(self) -> None:
        """Each template's `variable_names` must actually appear as
        `{{ }}` placeholders in its own text — otherwise AI Foundation's
        `PromptRenderer` would reject it at render time
        (`InvalidPromptTemplateError`)."""
        for template in build_all_templates():
            for variable_name in template.variable_names:
                assert f"{{{{ {variable_name} }}}}" in template.template_string
