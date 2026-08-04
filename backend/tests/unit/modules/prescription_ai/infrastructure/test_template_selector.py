"""Unit tests for `DefaultPrescriptionTemplateSelector`."""

import pytest

from app.modules.prescription_ai.domain.enums import PrescribingSetting
from app.modules.prescription_ai.infrastructure.prompts.template_selector import (
    DefaultPrescriptionTemplateSelector,
)
from app.modules.prescription_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)


class TestDefaultPrescriptionTemplateSelector:
    @pytest.mark.parametrize("prescribing_setting", list(PrescribingSetting))
    def test_selects_the_matching_template_names_for_every_setting(
        self, prescribing_setting: PrescribingSetting
    ) -> None:
        selector = DefaultPrescriptionTemplateSelector()

        template_set = selector.select(prescribing_setting)

        assert template_set.system_template_name == system_template_name(prescribing_setting)
        assert template_set.developer_template_name == developer_template_name(prescribing_setting)
        assert template_set.user_template_name == user_template_name(prescribing_setting)

    def test_defaults_to_version_one(self) -> None:
        selector = DefaultPrescriptionTemplateSelector()
        template_set = selector.select(PrescribingSetting.OUTPATIENT)
        assert template_set.version == 1

    def test_accepts_a_pinned_version(self) -> None:
        selector = DefaultPrescriptionTemplateSelector(version=2)
        template_set = selector.select(PrescribingSetting.OUTPATIENT)
        assert template_set.version == 2
