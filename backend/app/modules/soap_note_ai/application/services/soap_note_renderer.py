"""`SOAPNoteRenderer` — pure, I/O-free formatting from a structured
`SOAPNote` into one of this task's three output shapes (JSON, Markdown,
plain text). Lives in `application/services/`, not `infrastructure/`, the
same placement `app.modules.clinical_note_ai.application.services
.clinical_note_renderer.ClinicalNoteRenderer` uses for itself: no
external port dependency, no I/O, just a plain concrete service.
"""

import json

from app.modules.soap_note_ai.domain.enums import SOAPNoteOutputFormat
from app.modules.soap_note_ai.domain.value_objects import SOAPNote


class SOAPNoteRenderer:
    def render(self, note: SOAPNote, target_format: SOAPNoteOutputFormat) -> str:
        if target_format is SOAPNoteOutputFormat.JSON:
            return self._render_json(note)
        if target_format is SOAPNoteOutputFormat.MARKDOWN:
            return self._render_markdown(note)
        return self._render_text(note)

    def _render_json(self, note: SOAPNote) -> str:
        payload = {section.name: section.content for section in note.sections}
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def _render_markdown(self, note: SOAPNote) -> str:
        return "\n\n".join(
            f"## {self._humanize(section.name)}\n\n{section.content}" for section in note.sections
        )

    def _render_text(self, note: SOAPNote) -> str:
        return "\n\n".join(
            f"{self._humanize(section.name).upper()}:\n{section.content}"
            for section in note.sections
        )

    def _humanize(self, section_name: str) -> str:
        return section_name.replace("_", " ").title()
