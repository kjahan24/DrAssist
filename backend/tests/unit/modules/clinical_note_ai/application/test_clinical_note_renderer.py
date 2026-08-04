"""Unit tests for `ClinicalNoteRenderer`."""

import json

from app.modules.clinical_note_ai.application.services.clinical_note_renderer import (
    ClinicalNoteRenderer,
)
from app.modules.clinical_note_ai.domain.enums import ClinicalNoteOutputFormat
from tests.unit.modules.clinical_note_ai.application.fakes import make_clinical_note


class TestRenderJSON:
    def test_produces_valid_json_with_all_section_keys(self) -> None:
        renderer = ClinicalNoteRenderer()
        note = make_clinical_note()

        rendered = renderer.render(note, ClinicalNoteOutputFormat.JSON)

        payload = json.loads(rendered)
        assert payload["chief_complaint"] == "Headache"
        assert payload["assessment"] == "Tension headache"
        assert set(payload.keys()) == {s.name for s in note.sections}


class TestRenderMarkdown:
    def test_produces_a_heading_per_section(self) -> None:
        renderer = ClinicalNoteRenderer()
        note = make_clinical_note()

        rendered = renderer.render(note, ClinicalNoteOutputFormat.MARKDOWN)

        assert "## Chief Complaint" in rendered
        assert "## Assessment" in rendered
        assert "Headache" in rendered

    def test_humanizes_snake_case_section_names(self) -> None:
        renderer = ClinicalNoteRenderer()
        note = make_clinical_note()

        rendered = renderer.render(note, ClinicalNoteOutputFormat.MARKDOWN)

        assert "## History Of Present Illness" in rendered


class TestRenderText:
    def test_produces_uppercase_labels_per_section(self) -> None:
        renderer = ClinicalNoteRenderer()
        note = make_clinical_note()

        rendered = renderer.render(note, ClinicalNoteOutputFormat.TEXT)

        assert "CHIEF COMPLAINT:" in rendered
        assert "ASSESSMENT:" in rendered
        assert "Headache" in rendered
