"""Unit tests for `DefaultTemplateSelector`."""

import pytest

from app.modules.clinical_note_ai.domain.enums import NoteStyle
from app.modules.clinical_note_ai.infrastructure.prompts.template_selector import (
    DefaultTemplateSelector,
)
from app.modules.clinical_note_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)


class TestDefaultTemplateSelector:
    @pytest.mark.parametrize("note_style", list(NoteStyle))
    def test_selects_the_matching_template_names_for_every_style(
        self, note_style: NoteStyle
    ) -> None:
        selector = DefaultTemplateSelector()

        template_set = selector.select(note_style)

        assert template_set.system_template_name == system_template_name(note_style)
        assert template_set.developer_template_name == developer_template_name(note_style)
        assert template_set.user_template_name == user_template_name(note_style)

    def test_defaults_to_version_one(self) -> None:
        selector = DefaultTemplateSelector()
        template_set = selector.select(NoteStyle.CONCISE)
        assert template_set.version == 1

    def test_accepts_a_pinned_version(self) -> None:
        selector = DefaultTemplateSelector(version=2)
        template_set = selector.select(NoteStyle.CONCISE)
        assert template_set.version == 2
