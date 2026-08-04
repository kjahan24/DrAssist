"""`extract_json_object` — the mechanical "strip a markdown code fence if
present, then `json.loads`, then confirm the result is an object" pattern
that `app.modules.ai_copilot`, `app.modules.clinical_note_ai`, and now
`app.modules.soap_note_ai` each independently needed for parsing an LLM's
JSON reply.

Lives in the shared kernel, not any one module — the same "why here, not
duplicated a third/fourth time" question `app.modules.soap_note_ai`'s own
`container.py` scope note answers in full: this function has **zero**
dependency on any `app.modules.*` type (pure stdlib `json`/`re`), so it
can live at this layer without violating `app/shared/` and `app/core/`
are never allowed to import from `app/modules/` rule
(`docs/backend-architecture/11_standards_and_conventions.md`) — unlike
provider selection or template registration, which genuinely need AI
Foundation's public types and therefore cannot move here (see
`app.modules.soap_note_ai.infrastructure.provider_selection`'s own
docstring for that half of the reuse story).

Raises plain `ValueError` (not a domain exception — this layer has no
business vocabulary to attach one to); each calling module's own parser
catches `ValueError` and re-raises its own local domain exception
(`InvalidClinicalNoteFormatError`, `InvalidSOAPNoteFormatError`, ...).
"""

import json
import re

_JSON_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```$", re.DOTALL)


def extract_json_object(raw_text: str) -> dict[str, object]:
    candidate = raw_text.strip()
    fence_match = _JSON_FENCE_PATTERN.match(candidate)
    if fence_match:
        candidate = fence_match.group(1).strip()

    if not candidate:
        raise ValueError("response was empty")

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError(f"expected a JSON object, got {type(parsed).__name__}")
    return parsed
