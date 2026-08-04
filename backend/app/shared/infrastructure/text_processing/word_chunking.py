"""`chunk_text_by_word` — the "simulate streaming by re-emitting a
complete response word by word" pattern
`app.modules.ai.infrastructure.llm.mock_provider.MockAIProvider
.stream_complete` and `app.modules.clinical_note_ai.infrastructure
.generation.clinical_note_generator.DefaultClinicalNoteGenerator
.stream_generate` both already use. Shared here so
`app.modules.soap_note_ai` (and any future AI-content module needing the
same "AI Foundation's public surface has no token-level streaming"
workaround — see `app.modules.clinical_note_ai.infrastructure.generation
.clinical_note_generator`'s own module docstring for the full reasoning)
does not reimplement the same word-splitting loop a third time. Zero
dependency on any `app.modules.*` type.
"""

from collections.abc import Iterator


def chunk_text_by_word(text: str) -> Iterator[tuple[str, bool]]:
    """Yields `(delta, is_final)` pairs that reconstruct `text` when its
    deltas are concatenated in order — the first word carries no leading
    space, every subsequent word is prefixed with one (so
    `"".join(delta for delta, _ in chunk_text_by_word(text)) == text`
    for any single-spaced `text`)."""
    words = text.split(" ")
    for index, word in enumerate(words):
        is_final = index == len(words) - 1
        delta = word if index == 0 else f" {word}"
        yield delta, is_final
