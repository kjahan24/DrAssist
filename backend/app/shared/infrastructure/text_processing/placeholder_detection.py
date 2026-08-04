"""`find_placeholder_marker` — scans text for common unresolved-
placeholder markers (`[insert...]`, `TBD`, `TODO`, `XXX`, `Lorem ipsum`,
...) that indicate an LLM left a template artifact in its response
instead of real content. Shared for the same reason
`json_extraction.py` is: zero dependency on any `app.modules.*` type, so
it can live in the shared kernel without violating the "`app/shared/`
never imports from `app/modules/`" rule, and every AI-content-generating
module (`ai_copilot`, `clinical_note_ai`, `soap_note_ai`) needs the exact
same check.
"""

import re

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


def find_placeholder_marker(text: str) -> str | None:
    """Returns the first matched placeholder substring, or `None` if
    `text` contains none of the recognized markers."""
    for pattern in _PLACEHOLDER_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None
