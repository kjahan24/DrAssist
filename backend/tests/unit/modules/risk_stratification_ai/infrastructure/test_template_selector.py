"""Unit tests for `DefaultRiskStratificationAnalysisTemplateSelector`."""

import pytest

from app.modules.risk_stratification_ai.domain.enums import RiskStratificationSetting
from app.modules.risk_stratification_ai.infrastructure.prompts.template_selector import (
    DefaultRiskStratificationAnalysisTemplateSelector,
)
from app.modules.risk_stratification_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)


class TestDefaultRiskStratificationAnalysisTemplateSelector:
    @pytest.mark.parametrize("risk_setting", list(RiskStratificationSetting))
    def test_selects_the_matching_template_names_for_every_setting(
        self, risk_setting: RiskStratificationSetting
    ) -> None:
        selector = DefaultRiskStratificationAnalysisTemplateSelector()

        template_set = selector.select(risk_setting)

        assert template_set.system_template_name == system_template_name(risk_setting)
        assert template_set.developer_template_name == developer_template_name(risk_setting)
        assert template_set.user_template_name == user_template_name(risk_setting)

    def test_defaults_to_version_one(self) -> None:
        selector = DefaultRiskStratificationAnalysisTemplateSelector()
        template_set = selector.select(RiskStratificationSetting.OUTPATIENT)
        assert template_set.version == 1

    def test_accepts_a_pinned_version(self) -> None:
        selector = DefaultRiskStratificationAnalysisTemplateSelector(version=2)
        template_set = selector.select(RiskStratificationSetting.OUTPATIENT)
        assert template_set.version == 2
