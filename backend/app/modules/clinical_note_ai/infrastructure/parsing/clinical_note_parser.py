"""`DefaultClinicalNoteParser` — the one concrete `ClinicalNoteParserPort`
implementation this task ships, per "OUTPUT PARSER — Create robust parser
that converts AI output into ClinicalNote DTO".

The AI is always prompted for a single fixed-shape JSON object (the
`_JSON_CONTRACT` in `infrastructure/prompts/templates.py`, applied
identically regardless of `output_format` — see `domain/value_objects
.py::ClinicalNote`'s own docstring for why the canonical internal
representation is always structured JSON, with markdown/text handled at
render time instead of by asking the model for them directly). This
parser is therefore always a JSON parser; `output_format` on the
`ClinicalNote` it returns is carried through only as a hint for
`RenderClinicalNoteUseCase`'s default target, not a different parsing
strategy.

Missing keys in the AI's JSON produce an **empty** section (`""`), not a
parse failure — "missing sections" is `ClinicalNoteValidatorPort`'s job
(a distinct pipeline stage per this task's own "VALIDATION" section), so
this parser stays purely mechanical: malformed JSON is the only thing
that fails parsing itself.
"""

import json
import re

from app.modules.clinical_note_ai.application.ports import ClinicalNoteParserPort
from app.modules.clinical_note_ai.domain.enums import (
    ClinicalNoteOutputFormat,
    ClinicalNoteSectionName,
)
from app.modules.clinical_note_ai.domain.exceptions import InvalidClinicalNoteFormatError
from app.modules.clinical_note_ai.domain.value_objects import ClinicalNote, ClinicalNoteSection

_JSON_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```$", re.DOTALL)


class DefaultClinicalNoteParser(ClinicalNoteParserPort):
    def parse(self, raw_text: str, *, output_format: ClinicalNoteOutputFormat) -> ClinicalNote:
        payload = self._parse_json_object(raw_text)

        sections = tuple(
            ClinicalNoteSection(
                name=section_name.value,
                content=str(payload.get(section_name.value, "") or "").strip(),
            )
            for section_name in ClinicalNoteSectionName
        )
        return ClinicalNote(sections=sections, raw_text=raw_text, output_format=output_format)

    def _parse_json_object(self, raw_text: str) -> dict[str, object]:
        candidate = raw_text.strip()
        fence_match = _JSON_FENCE_PATTERN.match(candidate)
        if fence_match:
            candidate = fence_match.group(1).strip()

        if not candidate:
            raise InvalidClinicalNoteFormatError("AI response was empty")

        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise InvalidClinicalNoteFormatError(f"malformed JSON: {exc}") from exc

        if not isinstance(parsed, dict):
            raise InvalidClinicalNoteFormatError(
                f"expected a JSON object, got {type(parsed).__name__}"
            )
        return parsed
