"""Unit tests for `HeuristicTokenizer`."""

from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.value_objects import AIModel
from app.modules.ai.infrastructure.tokenizers.heuristic_tokenizer import HeuristicTokenizer

_MODEL = AIModel(provider=AIProviderType.MOCK, name="mock-model")


class TestHeuristicTokenizer:
    def test_empty_text_is_zero_tokens(self) -> None:
        assert HeuristicTokenizer().count_tokens(text="", model=_MODEL) == 0

    def test_short_text_is_at_least_one_token(self) -> None:
        assert HeuristicTokenizer().count_tokens(text="hi", model=_MODEL) >= 1

    def test_longer_text_yields_more_tokens(self) -> None:
        tokenizer = HeuristicTokenizer()
        short = tokenizer.count_tokens(text="hi", model=_MODEL)
        long = tokenizer.count_tokens(text="hi " * 100, model=_MODEL)
        assert long > short

    def test_scales_roughly_with_character_count(self) -> None:
        tokenizer = HeuristicTokenizer()
        text = "a" * 400
        assert tokenizer.count_tokens(text=text, model=_MODEL) == 100
