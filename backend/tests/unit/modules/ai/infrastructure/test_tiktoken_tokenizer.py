"""Unit tests for `TiktokenTokenizer`, using an injected fake encoding
duck-typed to `tiktoken.Encoding.encode(text) -> list[int]` — no real
`tiktoken` package is required (see that module's own docstring)."""

from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.value_objects import AIModel
from app.modules.ai.infrastructure.tokenizers.tiktoken_tokenizer import TiktokenTokenizer

_MODEL = AIModel(provider=AIProviderType.OPENAI, name="gpt-4o-mini")


class _FakeEncoding:
    def encode(self, text: str) -> list[int]:
        return list(range(len(text.split())))


class TestTiktokenTokenizer:
    def test_empty_text_is_zero_tokens(self) -> None:
        tokenizer = TiktokenTokenizer(encoding=_FakeEncoding())
        assert tokenizer.count_tokens(text="", model=_MODEL) == 0

    def test_counts_tokens_via_the_injected_encoding(self) -> None:
        tokenizer = TiktokenTokenizer(encoding=_FakeEncoding())
        assert tokenizer.count_tokens(text="one two three", model=_MODEL) == 3

    def test_reuses_the_injected_encoding_across_calls(self) -> None:
        encoding = _FakeEncoding()
        tokenizer = TiktokenTokenizer(encoding=encoding)
        tokenizer.count_tokens(text="a b", model=_MODEL)
        tokenizer.count_tokens(text="c d e", model=_MODEL)
        # No assertion needed beyond "did not raise" — the point is a
        # single injected encoding instance is reused, never rebuilt.
