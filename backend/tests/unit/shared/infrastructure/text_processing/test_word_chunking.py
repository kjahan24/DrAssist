"""Unit tests for `chunk_text_by_word`."""

from app.shared.infrastructure.text_processing.word_chunking import chunk_text_by_word


class TestChunkTextByWord:
    def test_reconstructs_the_original_text_when_deltas_are_joined(self) -> None:
        text = "one two three four"
        chunks = list(chunk_text_by_word(text))
        assert "".join(delta for delta, _ in chunks) == text

    def test_only_the_last_chunk_is_final(self) -> None:
        chunks = list(chunk_text_by_word("one two three"))
        assert all(not is_final for _delta, is_final in chunks[:-1])
        assert chunks[-1][1] is True

    def test_single_word_text_yields_one_final_chunk(self) -> None:
        chunks = list(chunk_text_by_word("hello"))
        assert len(chunks) == 1
        assert chunks[0] == ("hello", True)

    def test_yields_one_chunk_per_word(self) -> None:
        chunks = list(chunk_text_by_word("a b c d e"))
        assert len(chunks) == 5

    def test_empty_text_yields_a_single_empty_final_chunk(self) -> None:
        chunks = list(chunk_text_by_word(""))
        assert chunks == [("", True)]
