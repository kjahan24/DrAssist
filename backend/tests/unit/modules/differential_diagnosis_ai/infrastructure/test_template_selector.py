"""Unit tests for `DefaultDifferentialDiagnosisTemplateSelector`."""

import pytest

from app.modules.differential_diagnosis_ai.domain.enums import ClinicalSetting
from app.modules.differential_diagnosis_ai.infrastructure.prompts.template_selector import (
    DefaultDifferentialDiagnosisTemplateSelector,
)
from app.modules.differential_diagnosis_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)


class TestDefaultDifferentialDiagnosisTemplateSelector:
    @pytest.mark.parametrize("clinical_setting", list(ClinicalSetting))
    def test_selects_the_matching_template_names_for_every_setting(
        self, clinical_setting: ClinicalSetting
    ) -> None:
        selector = DefaultDifferentialDiagnosisTemplateSelector()

        template_set = selector.select(clinical_setting)

        assert template_set.system_template_name == system_template_name(clinical_setting)
        assert template_set.developer_template_name == developer_template_name(clinical_setting)
        assert template_set.user_template_name == user_template_name(clinical_setting)

    def test_defaults_to_version_one(self) -> None:
        selector = DefaultDifferentialDiagnosisTemplateSelector()
        template_set = selector.select(ClinicalSetting.OUTPATIENT)
        assert template_set.version == 1

    def test_accepts_a_pinned_version(self) -> None:
        selector = DefaultDifferentialDiagnosisTemplateSelector(version=2)
        template_set = selector.select(ClinicalSetting.OUTPATIENT)
        assert template_set.version == 2
