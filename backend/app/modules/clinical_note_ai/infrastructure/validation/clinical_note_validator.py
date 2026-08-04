"""`DefaultClinicalNoteValidator` — the one concrete
`ClinicalNoteValidatorPort` implementation this task ships, per
"VALIDATION — missing sections, empty responses, hallucinated
placeholders, invalid formatting" (the fourth, "invalid formatting", is
`ClinicalNoteParserPort`'s concern — a note that reaches this validator
already parsed successfully, so only content-level checks remain here).

Checks run in this order, each a distinct failure mode with its own
domain exception:

1. Every canonical section blank -> `EmptyAIResponseError` (the whole
   response is unusable, not just one section).
2. Any canonical section individually blank -> `MissingClinicalNoteSectionError`.
3. Any section containing a recognized placeholder marker (`[insert...]`,
   `TBD`, `TODO`, `XXX`, `Lorem ipsum`, ...) -> `HallucinatedPlaceholderError`.
"""

import re

from app.modules.clinical_note_ai.application.ports import ClinicalNoteValidatorPort
from app.modules.clinical_note_ai.domain.enums import ClinicalNoteSectionName
from app.modules.clinical_note_ai.domain.exceptions import (
    EmptyAIResponseError,
    HallucinatedPlaceholderError,
    MissingClinicalNoteSectionError,
)
from app.modules.clinical_note_ai.domain.value_objects import ClinicalNote

_PLACEHOLDER_PATTERNS = [
    re.compile(r"\[\s*insert.*?\]", re.IGNORECASE),
    re.compile(r"\[\s*placeholder.*?\]", re.IGNORECASE),
    re.compile(r"<\s*insert.*?>", re.IGNORECASE),
    re.compile(r"\btbd\b", re.IGNORECASE),
    re.compile(r"\btodo\b", re.IGNORECASE),
    re.compile(r"\bxxx+\b", re.IGNORECASE),
    re.compile(r"lorem ipsum", re.IGNORECASE),
    re.compile(r"\[\s*patient name\s*\]", re.IGNORECASE),
]


class DefaultClinicalNoteValidator(ClinicalNoteValidatorPort):
    def validate(self, note: ClinicalNote) -> None:
        canonical_sections = [
            (section_name.value, note.get_section(section_name.value) or "")
            for section_name in ClinicalNoteSectionName
        ]

        if all(not content.strip() for _name, content in canonical_sections):
            raise EmptyAIResponseError()

        for name, content in canonical_sections:
            if not content.strip():
                raise MissingClinicalNoteSectionError(name)

        for name, content in canonical_sections:
            for pattern in _PLACEHOLDER_PATTERNS:
                match = pattern.search(content)
                if match:
                    raise HallucinatedPlaceholderError(name, match.group(0))
