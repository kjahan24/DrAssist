"""`TiktokenTokenizer` — an exact, OpenAI-model-accurate `TokenizerPort`
implementation, wrapping the `tiktoken` package.

`tiktoken` is **not** in `requirements/base.txt` (kept optional so the
rest of this module never requires it) — imported lazily inside
`_get_encoding`, the same lazy-import-for-optional-dependency pattern
`infrastructure/llm/openai_provider.py` uses for the `openai` SDK. An
`encoding` may be injected directly (duck-typed to `tiktoken`'s
`Encoding.encode(text) -> list[int]`) so unit tests never need the real
package installed.
"""

from typing import Any

from app.modules.ai.application.ports import TokenizerPort
from app.modules.ai.domain.value_objects import AIModel

_DEFAULT_ENCODING_NAME = "cl100k_base"


class TiktokenTokenizer(TokenizerPort):
    def __init__(self, *, encoding: Any | None = None) -> None:
        self._encoding = encoding

    def _get_encoding(self, model_name: str) -> Any:
        if self._encoding is not None:
            return self._encoding
        import tiktoken

        try:
            self._encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            self._encoding = tiktoken.get_encoding(_DEFAULT_ENCODING_NAME)
        return self._encoding

    def count_tokens(self, *, text: str, model: AIModel) -> int:
        if not text:
            return 0
        encoding = self._get_encoding(model.name)
        return len(encoding.encode(text))
