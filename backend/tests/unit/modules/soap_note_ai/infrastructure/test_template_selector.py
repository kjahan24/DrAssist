"""Unit tests for `DefaultSOAPTemplateSelector`."""

import pytest

from app.modules.soap_note_ai.domain.enums import SOAPStyle
from app.modules.soap_note_ai.infrastructure.prompts.template_selector import (
    DefaultSOAPTemplateSelector,
)
from app.modules.soap_note_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)


class TestDefaultSOAPTemplateSelector:
    @pytest.mark.parametrize("soap_style", list(SOAPStyle))
    def test_selects_the_matching_template_names_for_every_style(
        self, soap_style: SOAPStyle
    ) -> None:
        selector = DefaultSOAPTemplateSelector()

        template_set = selector.select(soap_style)

        assert template_set.system_template_name == system_template_name(soap_style)
        assert template_set.developer_template_name == developer_template_name(soap_style)
        assert template_set.user_template_name == user_template_name(soap_style)

    def test_defaults_to_version_one(self) -> None:
        selector = DefaultSOAPTemplateSelector()
        template_set = selector.select(SOAPStyle.CONCISE)
        assert template_set.version == 1

    def test_accepts_a_pinned_version(self) -> None:
        selector = DefaultSOAPTemplateSelector(version=2)
        template_set = selector.select(SOAPStyle.CONCISE)
        assert template_set.version == 2
