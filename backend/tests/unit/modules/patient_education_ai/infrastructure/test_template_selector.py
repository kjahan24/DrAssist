"""Unit tests for `DefaultPatientEducationAnalysisTemplateSelector`."""

import pytest

from app.modules.patient_education_ai.domain.enums import PatientEducationSetting
from app.modules.patient_education_ai.infrastructure.prompts.template_selector import (
    DefaultPatientEducationAnalysisTemplateSelector,
)
from app.modules.patient_education_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)


class TestDefaultPatientEducationAnalysisTemplateSelector:
    @pytest.mark.parametrize("education_setting", list(PatientEducationSetting))
    def test_selects_the_matching_template_names_for_every_setting(
        self, education_setting: PatientEducationSetting
    ) -> None:
        selector = DefaultPatientEducationAnalysisTemplateSelector()

        template_set = selector.select(education_setting)

        assert template_set.system_template_name == system_template_name(education_setting)
        assert template_set.developer_template_name == developer_template_name(education_setting)
        assert template_set.user_template_name == user_template_name(education_setting)

    def test_defaults_to_version_one(self) -> None:
        selector = DefaultPatientEducationAnalysisTemplateSelector()
        template_set = selector.select(PatientEducationSetting.ADULT)
        assert template_set.version == 1

    def test_accepts_a_pinned_version(self) -> None:
        selector = DefaultPatientEducationAnalysisTemplateSelector(version=2)
        template_set = selector.select(PatientEducationSetting.ADULT)
        assert template_set.version == 2
