"""Unit tests for `DefaultRadiologyInterpretationTemplateSelector`."""

import pytest

from app.modules.radiology_interpretation_ai.domain.enums import RadiologySetting
from app.modules.radiology_interpretation_ai.infrastructure.prompts.template_selector import (
    DefaultRadiologyInterpretationTemplateSelector,
)
from app.modules.radiology_interpretation_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)


class TestDefaultRadiologyInterpretationTemplateSelector:
    @pytest.mark.parametrize("radiology_setting", list(RadiologySetting))
    def test_selects_the_matching_template_names_for_every_setting(
        self, radiology_setting: RadiologySetting
    ) -> None:
        selector = DefaultRadiologyInterpretationTemplateSelector()

        template_set = selector.select(radiology_setting)

        assert template_set.system_template_name == system_template_name(radiology_setting)
        assert template_set.developer_template_name == developer_template_name(radiology_setting)
        assert template_set.user_template_name == user_template_name(radiology_setting)

    def test_defaults_to_version_one(self) -> None:
        selector = DefaultRadiologyInterpretationTemplateSelector()
        template_set = selector.select(RadiologySetting.OUTPATIENT)
        assert template_set.version == 1

    def test_accepts_a_pinned_version(self) -> None:
        selector = DefaultRadiologyInterpretationTemplateSelector(version=2)
        template_set = selector.select(RadiologySetting.OUTPATIENT)
        assert template_set.version == 2
