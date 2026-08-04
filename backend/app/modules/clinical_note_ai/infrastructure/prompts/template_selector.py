"""`DefaultTemplateSelector` — the one concrete `TemplateSelectorPort`
implementation this task ships: maps a `NoteStyle` onto the three
registered AI Foundation prompt template names
(`infrastructure/prompts/templates.py`) plus the pinned version to use.

A plain, static mapping (not configuration-driven) — this task's own
"Implement template selection" requirement is about resolving style ->
templates, not about A/B-testing or per-organization template overrides,
which are out of scope until a real need motivates them.
"""

from app.modules.clinical_note_ai.application.ports import TemplateSelectorPort
from app.modules.clinical_note_ai.domain.enums import NoteStyle
from app.modules.clinical_note_ai.domain.value_objects import ClinicalNoteTemplateSet
from app.modules.clinical_note_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)

_DEFAULT_VERSION = 1


class DefaultTemplateSelector(TemplateSelectorPort):
    def __init__(self, *, version: int = _DEFAULT_VERSION) -> None:
        self._version = version

    def select(self, note_style: NoteStyle) -> ClinicalNoteTemplateSet:
        return ClinicalNoteTemplateSet(
            system_template_name=system_template_name(note_style),
            developer_template_name=developer_template_name(note_style),
            user_template_name=user_template_name(note_style),
            version=self._version,
        )
