"""Unit tests for `DefaultPathologyInterpretationTemplateSelector`."""

import pytest

from app.modules.pathology_interpretation_ai.domain.enums import PathologySetting
from app.modules.pathology_interpretation_ai.infrastructure.prompts.template_selector import (
    DefaultPathologyInterpretationTemplateSelector,
)
from app.modules.pathology_interpretation_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)


class TestDefaultPathologyInterpretationTemplateSelector:
    @pytest.mark.parametrize("pathology_setting", list(PathologySetting))
    def test_selects_the_matching_template_names_for_every_setting(
        self, pathology_setting: PathologySetting
    ) -> None:
        selector = DefaultPathologyInterpretationTemplateSelector()

        template_set = selector.select(pathology_setting)

        assert template_set.system_template_name == system_template_name(pathology_setting)
        assert template_set.developer_template_name == developer_template_name(pathology_setting)
        assert template_set.user_template_name == user_template_name(pathology_setting)

    def test_defaults_to_version_one(self) -> None:
        selector = DefaultPathologyInterpretationTemplateSelector()
        template_set = selector.select(PathologySetting.OUTPATIENT)
        assert template_set.version == 1

    def test_accepts_a_pinned_version(self) -> None:
        selector = DefaultPathologyInterpretationTemplateSelector(version=2)
        template_set = selector.select(PathologySetting.OUTPATIENT)
        assert template_set.version == 2
