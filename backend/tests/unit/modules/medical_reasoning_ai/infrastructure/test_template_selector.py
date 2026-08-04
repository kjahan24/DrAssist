"""Unit tests for `DefaultMedicalReasoningTemplateSelector`."""

import pytest

from app.modules.medical_reasoning_ai.domain.enums import ReasoningSetting
from app.modules.medical_reasoning_ai.infrastructure.prompts.template_selector import (
    DefaultMedicalReasoningTemplateSelector,
)
from app.modules.medical_reasoning_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)


class TestDefaultMedicalReasoningTemplateSelector:
    @pytest.mark.parametrize("reasoning_setting", list(ReasoningSetting))
    def test_selects_the_matching_template_names_for_every_setting(
        self, reasoning_setting: ReasoningSetting
    ) -> None:
        selector = DefaultMedicalReasoningTemplateSelector()

        template_set = selector.select(reasoning_setting)

        assert template_set.system_template_name == system_template_name(reasoning_setting)
        assert template_set.developer_template_name == developer_template_name(reasoning_setting)
        assert template_set.user_template_name == user_template_name(reasoning_setting)

    def test_defaults_to_version_one(self) -> None:
        selector = DefaultMedicalReasoningTemplateSelector()
        template_set = selector.select(ReasoningSetting.OUTPATIENT)
        assert template_set.version == 1

    def test_accepts_a_pinned_version(self) -> None:
        selector = DefaultMedicalReasoningTemplateSelector(version=2)
        template_set = selector.select(ReasoningSetting.OUTPATIENT)
        assert template_set.version == 2
