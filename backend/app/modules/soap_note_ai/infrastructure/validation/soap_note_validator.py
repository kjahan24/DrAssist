"""`DefaultSOAPNoteValidator` — the one concrete `SOAPNoteValidatorPort`
implementation this task ships, per "VALIDATION — missing SOAP sections,
empty outputs, malformed JSON, duplicated sections, hallucinated
placeholders, invalid markdown" ("malformed JSON" is
`SOAPNoteParserPort`'s concern — a note that reaches this validator
already parsed successfully, so only content-level checks remain here,
the same split `app.modules.clinical_note_ai.infrastructure.validation
.clinical_note_validator.DefaultClinicalNoteValidator` documents for
itself).

Reuses `app.shared.infrastructure.text_processing.placeholder_detection
.find_placeholder_marker` (rule: "Reuse... Validation utilities... Avoid
duplicate implementations").

Checks run in this order, each a distinct failure mode with its own
domain exception:

1. Every canonical section blank -> `EmptySOAPResponseError`.
2. Any canonical section individually blank -> `MissingSOAPSectionError`.
3. Two different canonical sections sharing identical non-blank content
   -> `DuplicatedSOAPSectionError` — `json.loads` silently collapses a
   literal duplicate JSON *key* to its last occurrence (so that specific
   malformation can never reach this validator at all), but a model
   copying the same sentence into two different section *values* is a
   real, observed failure mode this catches instead.
4. Any section containing a recognized placeholder marker ->
   `HallucinatedPlaceholderError`.
5. Any section containing unbalanced markdown fence (`` ``` ``) or bold
   (`**`) markers -> `InvalidMarkdownFormatError` — guards against
   content that would render broken once
   `application/services/soap_note_renderer.py` emits it as Markdown,
   even though the section value itself is plain JSON-string text.
"""

from app.modules.soap_note_ai.application.ports import SOAPNoteValidatorPort
from app.modules.soap_note_ai.domain.enums import SOAPSectionName
from app.modules.soap_note_ai.domain.exceptions import (
    DuplicatedSOAPSectionError,
    EmptySOAPResponseError,
    HallucinatedPlaceholderError,
    InvalidMarkdownFormatError,
    MissingSOAPSectionError,
)
from app.modules.soap_note_ai.domain.value_objects import SOAPNote
from app.shared.infrastructure.text_processing.placeholder_detection import (
    find_placeholder_marker,
)

_UNBALANCED_MARKERS = {"```": "code fence", "**": "bold marker"}


class DefaultSOAPNoteValidator(SOAPNoteValidatorPort):
    def validate(self, note: SOAPNote) -> None:
        canonical_sections = [
            (section_name.value, note.get_section(section_name.value) or "")
            for section_name in SOAPSectionName
        ]

        if all(not content.strip() for _name, content in canonical_sections):
            raise EmptySOAPResponseError()

        for name, content in canonical_sections:
            if not content.strip():
                raise MissingSOAPSectionError(name)

        self._check_duplicated_sections(canonical_sections)

        for name, content in canonical_sections:
            placeholder = find_placeholder_marker(content)
            if placeholder is not None:
                raise HallucinatedPlaceholderError(name, placeholder)

        for name, content in canonical_sections:
            self._check_markdown_balance(name, content)

    def _check_duplicated_sections(self, canonical_sections: list[tuple[str, str]]) -> None:
        seen: dict[str, str] = {}
        for name, content in canonical_sections:
            normalized = content.strip().lower()
            for other_name, other_content in seen.items():
                if normalized == other_content:
                    raise DuplicatedSOAPSectionError(other_name, name)
            seen[name] = normalized

    def _check_markdown_balance(self, name: str, content: str) -> None:
        for marker, label in _UNBALANCED_MARKERS.items():
            if content.count(marker) % 2 != 0:
                raise InvalidMarkdownFormatError(name, f"unbalanced {label} ({marker!r})")
