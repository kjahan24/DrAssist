"""`DefaultCopilotOutputParser` — the one concrete
`CopilotOutputParserPort` implementation this task ships, supporting the
three `CopilotOutputFormat` values this task specifies: JSON, Markdown,
plain text.

Independent of, and not sharing code with, AI Foundation's own
`infrastructure/parsers/json_parser.py::JSONResponseParser` — that class
lives in AI Foundation's `infrastructure/`, not its `public/`, so this
module cannot import it (module-independence rule); the fenced-code-block
stripping logic is small enough that duplicating it locally (the same
"each module defines its own copy" pattern documented throughout this
codebase) is simpler than inventing a shared-kernel abstraction for a
two-module need.
"""

import json
import re

from app.modules.ai_copilot.application.ports import CopilotOutputParserPort
from app.modules.ai_copilot.domain.enums import CopilotOutputFormat
from app.modules.ai_copilot.domain.exceptions import StructuredResponseParsingError

_JSON_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```$", re.DOTALL)
_MARKDOWN_HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)


class DefaultCopilotOutputParser(CopilotOutputParserPort):
    def parse(self, raw_text: str, output_format: CopilotOutputFormat) -> object:
        if output_format is CopilotOutputFormat.JSON:
            return self._parse_json(raw_text)
        if output_format is CopilotOutputFormat.MARKDOWN:
            return self._parse_markdown(raw_text)
        return raw_text.strip()

    def _parse_json(self, raw_text: str) -> object:
        candidate = raw_text.strip()
        fence_match = _JSON_FENCE_PATTERN.match(candidate)
        if fence_match:
            candidate = fence_match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise StructuredResponseParsingError("json", str(exc)) from exc

    def _parse_markdown(self, raw_text: str) -> dict[str, str]:
        """Splits on `#`/`##`/... headings into `{heading: body}` —
        content before the first heading (if any) is discarded only when
        blank; a document with no headings at all becomes a single
        `{"content": ...}` entry."""
        text = raw_text.strip()
        headings = list(_MARKDOWN_HEADING_PATTERN.finditer(text))
        if not headings:
            if not text:
                raise StructuredResponseParsingError("markdown", "response was empty")
            return {"content": text}

        sections: dict[str, str] = {}
        for index, match in enumerate(headings):
            heading = match.group(1).strip()
            body_start = match.end()
            body_end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            sections[heading] = text[body_start:body_end].strip()
        return sections
