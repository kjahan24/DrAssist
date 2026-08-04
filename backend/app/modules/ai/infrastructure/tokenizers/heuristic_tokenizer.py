"""`HeuristicTokenizer` — the default, dependency-free `TokenizerPort`
implementation: a characters-per-token approximation (~4 characters per
English token, a widely-used rule of thumb for GPT-family tokenizers).

Deliberately not exact — no tokenizer package (`tiktoken` or similar) is a
base dependency of this project yet (`requirements/base.txt`), and every
provider's *real* token accounting already comes back on
`ChatCompletionResponse.usage`/`EmbeddingResponse.usage` directly from the
API response, which is authoritative. This tokenizer exists for the one
case that matters before a call is made — estimating whether a prompt
will fit a model's `context_window` — where an approximation is
sufficient. See `tiktoken_tokenizer.py` for a provider-accurate
alternative behind the same `TokenizerPort`, swappable without any caller
change.
"""

from app.modules.ai.application.ports import TokenizerPort
from app.modules.ai.domain.value_objects import AIModel

_CHARS_PER_TOKEN = 4


class HeuristicTokenizer(TokenizerPort):
    def count_tokens(self, *, text: str, model: AIModel) -> int:
        if not text:
            return 0
        return max(1, len(text) // _CHARS_PER_TOKEN)
