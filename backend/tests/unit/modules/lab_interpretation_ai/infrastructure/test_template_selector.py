"""Unit tests for `DefaultLabInterpretationTemplateSelector`."""

import pytest

from app.modules.lab_interpretation_ai.domain.enums import LabInterpretationSetting
from app.modules.lab_interpretation_ai.infrastructure.prompts.template_selector import (
    DefaultLabInterpretationTemplateSelector,
)
from app.modules.lab_interpretation_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)


class TestDefaultLabInterpretationTemplateSelector:
    @pytest.mark.parametrize("lab_setting", list(LabInterpretationSetting))
    def test_selects_the_matching_template_names_for_every_setting(
        self, lab_setting: LabInterpretationSetting
    ) -> None:
        selector = DefaultLabInterpretationTemplateSelector()

        template_set = selector.select(lab_setting)

        assert template_set.system_template_name == system_template_name(lab_setting)
        assert template_set.developer_template_name == developer_template_name(lab_setting)
        assert template_set.user_template_name == user_template_name(lab_setting)

    def test_defaults_to_version_one(self) -> None:
        selector = DefaultLabInterpretationTemplateSelector()
        template_set = selector.select(LabInterpretationSetting.OUTPATIENT)
        assert template_set.version == 1

    def test_accepts_a_pinned_version(self) -> None:
        selector = DefaultLabInterpretationTemplateSelector(version=2)
        template_set = selector.select(LabInterpretationSetting.OUTPATIENT)
        assert template_set.version == 2
