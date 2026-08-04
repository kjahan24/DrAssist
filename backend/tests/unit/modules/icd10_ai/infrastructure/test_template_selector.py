"""Unit tests for `DefaultICD10TemplateSelector`."""

import pytest

from app.modules.icd10_ai.domain.enums import CodingSetting
from app.modules.icd10_ai.infrastructure.prompts.template_selector import (
    DefaultICD10TemplateSelector,
)
from app.modules.icd10_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)


class TestDefaultICD10TemplateSelector:
    @pytest.mark.parametrize("coding_setting", list(CodingSetting))
    def test_selects_the_matching_template_names_for_every_setting(
        self, coding_setting: CodingSetting
    ) -> None:
        selector = DefaultICD10TemplateSelector()

        template_set = selector.select(coding_setting)

        assert template_set.system_template_name == system_template_name(coding_setting)
        assert template_set.developer_template_name == developer_template_name(coding_setting)
        assert template_set.user_template_name == user_template_name(coding_setting)

    def test_defaults_to_version_one(self) -> None:
        selector = DefaultICD10TemplateSelector()
        template_set = selector.select(CodingSetting.OUTPATIENT)
        assert template_set.version == 1

    def test_accepts_a_pinned_version(self) -> None:
        selector = DefaultICD10TemplateSelector(version=2)
        template_set = selector.select(CodingSetting.OUTPATIENT)
        assert template_set.version == 2
