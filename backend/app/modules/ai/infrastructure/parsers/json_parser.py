"""`JSONResponseParser` — the one concrete `StructuredResponseParserPort`
implementation this task ships.

LLMs asked for JSON frequently wrap it in a markdown code fence (` ```json
... ``` `) or add leading/trailing prose despite instructions not to —
`parse()` strips a single leading/trailing fence before attempting
`json.loads`, so a caller depending on `ChatCompletionRequest
.response_format="json"` doesn't need to reimplement this cleanup at every
call site.
"""

import json
import re

from app.modules.ai.application.ports import StructuredResponseParserPort
from app.modules.ai.domain.exceptions import AIProviderResponseParsingError

_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```$", re.DOTALL)


class JSONResponseParser(StructuredResponseParserPort):
    def parse(self, raw_text: str) -> object:
        candidate = raw_text.strip()
        fence_match = _FENCE_PATTERN.match(candidate)
        if fence_match:
            candidate = fence_match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise AIProviderResponseParsingError(
                provider="unknown", message=f"could not parse JSON response: {exc}"
            ) from exc
