"""Unit tests for `DefaultDrugSafetyAnalysisTemplateSelector`."""

import pytest

from app.modules.drug_interaction_ai.domain.enums import DrugInteractionSetting
from app.modules.drug_interaction_ai.infrastructure.prompts.template_selector import (
    DefaultDrugSafetyAnalysisTemplateSelector,
)
from app.modules.drug_interaction_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)


class TestDefaultDrugSafetyAnalysisTemplateSelector:
    @pytest.mark.parametrize("medication_setting", list(DrugInteractionSetting))
    def test_selects_the_matching_template_names_for_every_setting(
        self, medication_setting: DrugInteractionSetting
    ) -> None:
        selector = DefaultDrugSafetyAnalysisTemplateSelector()

        template_set = selector.select(medication_setting)

        assert template_set.system_template_name == system_template_name(medication_setting)
        assert template_set.developer_template_name == developer_template_name(medication_setting)
        assert template_set.user_template_name == user_template_name(medication_setting)

    def test_defaults_to_version_one(self) -> None:
        selector = DefaultDrugSafetyAnalysisTemplateSelector()
        template_set = selector.select(DrugInteractionSetting.OUTPATIENT)
        assert template_set.version == 1

    def test_accepts_a_pinned_version(self) -> None:
        selector = DefaultDrugSafetyAnalysisTemplateSelector(version=2)
        template_set = selector.select(DrugInteractionSetting.OUTPATIENT)
        assert template_set.version == 2
