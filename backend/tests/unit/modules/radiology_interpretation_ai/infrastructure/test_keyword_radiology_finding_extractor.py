"""Unit tests for `KeywordRadiologyFindingExtractor`."""

import pytest

from app.modules.radiology_interpretation_ai.domain.enums import RadiologyFindingCategory
from app.modules.radiology_interpretation_ai.infrastructure.finding_extraction.keyword_radiology_finding_extractor import (  # noqa: E501
    KeywordRadiologyFindingExtractor,
)


class TestExtractCandidateFindings:
    def test_returns_empty_tuple_for_text_with_no_recognized_keywords(self) -> None:
        extractor = KeywordRadiologyFindingExtractor()
        assert extractor.extract_candidate_findings("The heart is of normal size.") == ()

    def test_extracts_a_critical_keyword_match(self) -> None:
        extractor = KeywordRadiologyFindingExtractor()

        candidates = extractor.extract_candidate_findings(
            "There is a large right-sided pneumothorax."
        )

        assert len(candidates) == 1
        assert candidates[0].category is RadiologyFindingCategory.CRITICAL
        assert candidates[0].description == "Pneumothorax"

    def test_extracts_a_normal_keyword_match(self) -> None:
        extractor = KeywordRadiologyFindingExtractor()

        candidates = extractor.extract_candidate_findings("Unremarkable study overall.")

        assert len(candidates) == 1
        assert candidates[0].category is RadiologyFindingCategory.NORMAL

    def test_extracts_multiple_distinct_keyword_matches(self) -> None:
        extractor = KeywordRadiologyFindingExtractor()

        candidates = extractor.extract_candidate_findings(
            "Findings concerning for pneumothorax and pulmonary embolism."
        )

        descriptions = {c.description for c in candidates}
        assert descriptions == {"Pneumothorax", "Embolism"}

    def test_is_case_insensitive(self) -> None:
        extractor = KeywordRadiologyFindingExtractor()

        candidates = extractor.extract_candidate_findings("PNEUMOTHORAX identified.")

        assert len(candidates) == 1

    @pytest.mark.parametrize(
        "keyword",
        [
            "pneumothorax",
            "hemorrhage",
            "rupture",
            "perforation",
            "obstruction",
            "mass effect",
            "midline shift",
            "herniation",
            "embolism",
            "dissection",
            "free air",
            "tamponade",
        ],
    )
    def test_recognizes_every_critical_keyword(self, keyword: str) -> None:
        extractor = KeywordRadiologyFindingExtractor()

        candidates = extractor.extract_candidate_findings(f"Report notes {keyword} present.")

        assert any(c.category is RadiologyFindingCategory.CRITICAL for c in candidates)

    @pytest.mark.parametrize(
        "keyword",
        [
            "no acute findings",
            "unremarkable",
            "within normal limits",
            "no significant abnormality",
            "no acute abnormality",
            "normal study",
        ],
    )
    def test_recognizes_every_normal_keyword(self, keyword: str) -> None:
        extractor = KeywordRadiologyFindingExtractor()

        candidates = extractor.extract_candidate_findings(f"Impression: {keyword}.")

        assert any(c.category is RadiologyFindingCategory.NORMAL for c in candidates)

    def test_accepts_a_custom_keyword_table(self) -> None:
        extractor = KeywordRadiologyFindingExtractor(
            critical_keywords=("custom critical phrase",), normal_keywords=()
        )

        candidates = extractor.extract_candidate_findings("Report mentions custom critical phrase.")

        assert len(candidates) == 1
        assert candidates[0].category is RadiologyFindingCategory.CRITICAL


class TestClassifyDescription:
    def test_returns_none_for_unrecognized_text(self) -> None:
        extractor = KeywordRadiologyFindingExtractor()
        assert extractor.classify_description("Heart size normal") is None

    def test_classifies_critical_language(self) -> None:
        extractor = KeywordRadiologyFindingExtractor()
        assert extractor.classify_description("Findings consistent with pneumothorax") is (
            RadiologyFindingCategory.CRITICAL
        )

    def test_classifies_normal_language(self) -> None:
        extractor = KeywordRadiologyFindingExtractor()
        assert extractor.classify_description("Unremarkable examination") is (
            RadiologyFindingCategory.NORMAL
        )

    def test_is_case_insensitive(self) -> None:
        extractor = KeywordRadiologyFindingExtractor()
        assert extractor.classify_description("HEMORRHAGE noted") is (
            RadiologyFindingCategory.CRITICAL
        )
