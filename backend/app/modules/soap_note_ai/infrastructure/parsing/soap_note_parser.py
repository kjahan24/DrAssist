"""`DefaultSOAPNoteParser` — the one concrete `SOAPNoteParserPort`
implementation this task ships, per "OUTPUT PARSER — Convert AI responses
into strongly typed SOAP DTOs."

Reuses `app.shared.infrastructure.text_processing.json_extraction
.extract_json_object` for the mechanical fence-stripping/`json.loads`
work (rule: "Reuse... Parser utilities... Avoid duplicate
implementations" — see that function's own docstring for why it lives in
the shared kernel rather than a third copy of the same regex).

The AI is always prompted for a single fixed-shape JSON object (the
`_JSON_CONTRACT` in `infrastructure/prompts/templates.py`) regardless of
`output_format` — see `domain/value_objects.py::SOAPNote`'s own docstring
for why the canonical internal representation is always structured JSON,
with markdown/text handled at render time instead.

Missing keys in the AI's JSON produce an **empty** section (`""`), not a
parse failure — "missing sections" is `SOAPNoteValidatorPort`'s job, so
this parser stays purely mechanical: malformed JSON is the only thing
that fails parsing itself.
"""

from app.modules.soap_note_ai.application.ports import SOAPNoteParserPort
from app.modules.soap_note_ai.domain.enums import SOAPNoteOutputFormat, SOAPSectionName
from app.modules.soap_note_ai.domain.exceptions import InvalidSOAPNoteFormatError
from app.modules.soap_note_ai.domain.value_objects import SOAPNote, SOAPSection
from app.shared.infrastructure.text_processing.json_extraction import extract_json_object


class DefaultSOAPNoteParser(SOAPNoteParserPort):
    def parse(self, raw_text: str, *, output_format: SOAPNoteOutputFormat) -> SOAPNote:
        try:
            payload = extract_json_object(raw_text)
        except ValueError as exc:
            raise InvalidSOAPNoteFormatError(str(exc)) from exc

        sections = tuple(
            SOAPSection(
                name=section_name.value,
                content=str(payload.get(section_name.value, "") or "").strip(),
            )
            for section_name in SOAPSectionName
        )
        return SOAPNote(sections=sections, raw_text=raw_text, output_format=output_format)
