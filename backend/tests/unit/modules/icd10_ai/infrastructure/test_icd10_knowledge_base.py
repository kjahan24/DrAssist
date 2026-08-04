"""Unit tests for `StaticICD10KnowledgeBase`."""

import pytest

from app.modules.icd10_ai.infrastructure.knowledge.icd10_knowledge_base import (
    StaticICD10KnowledgeBase,
)


class TestIsValidFormat:
    @pytest.mark.parametrize(
        "code",
        ["J06.9", "I10", "E11.9", "S72.001A", "M54.5", "R51", "O80", "Z00.00"],
    )
    def test_accepts_structurally_valid_codes(self, code: str) -> None:
        knowledge = StaticICD10KnowledgeBase()
        assert knowledge.is_valid_format(code) is True

    @pytest.mark.parametrize(
        "code",
        ["", "NOTACODE", "1J06.9", "U07.1", "J6.9", "J06..9", "12", "J", "J-06"],
    )
    def test_rejects_structurally_invalid_codes(self, code: str) -> None:
        knowledge = StaticICD10KnowledgeBase()
        assert knowledge.is_valid_format(code) is False

    def test_is_case_insensitive(self) -> None:
        knowledge = StaticICD10KnowledgeBase()
        assert knowledge.is_valid_format("j06.9") is True

    def test_strips_surrounding_whitespace(self) -> None:
        knowledge = StaticICD10KnowledgeBase()
        assert knowledge.is_valid_format("  J06.9  ") is True


class TestLookupCanonicalName:
    def test_returns_the_description_for_a_recognized_common_code(self) -> None:
        knowledge = StaticICD10KnowledgeBase()
        assert knowledge.lookup_canonical_name("J06.9") is not None

    def test_returns_none_for_a_code_not_in_the_curated_set(self) -> None:
        knowledge = StaticICD10KnowledgeBase()
        assert knowledge.lookup_canonical_name("Z99.9") is None

    def test_is_case_insensitive(self) -> None:
        knowledge = StaticICD10KnowledgeBase()
        assert knowledge.lookup_canonical_name("j06.9") == knowledge.lookup_canonical_name("J06.9")
