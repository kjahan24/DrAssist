"""`ClinicalNoteRenderer` — pure, I/O-free formatting from a structured
`ClinicalNote` into one of this task's three output shapes (JSON,
Markdown, plain text). Lives in `application/services/`, not
`infrastructure/` — the same placement
`app.modules.ai_copilot.application.services.prompt_builder.PromptBuilder`
uses for itself: no external port dependency, no I/O, just a plain
concrete service (this task did not ask for a swappable "renderer port"
the way it did for `ClinicalNoteGeneratorPort`/`PromptBuilderPort`/
`TemplateSelectorPort`).
"""

import json

from app.modules.clinical_note_ai.domain.enums import ClinicalNoteOutputFormat
from app.modules.clinical_note_ai.domain.value_objects import ClinicalNote


class ClinicalNoteRenderer:
    def render(self, note: ClinicalNote, target_format: ClinicalNoteOutputFormat) -> str:
        if target_format is ClinicalNoteOutputFormat.JSON:
            return self._render_json(note)
        if target_format is ClinicalNoteOutputFormat.MARKDOWN:
            return self._render_markdown(note)
        return self._render_text(note)

    def _render_json(self, note: ClinicalNote) -> str:
        payload = {section.name: section.content for section in note.sections}
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def _render_markdown(self, note: ClinicalNote) -> str:
        return "\n\n".join(
            f"## {self._humanize(section.name)}\n\n{section.content}" for section in note.sections
        )

    def _render_text(self, note: ClinicalNote) -> str:
        return "\n\n".join(
            f"{self._humanize(section.name).upper()}:\n{section.content}"
            for section in note.sections
        )

    def _humanize(self, section_name: str) -> str:
        return section_name.replace("_", " ").title()
