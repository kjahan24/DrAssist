"""Unit tests for `KeywordClinicalCorrelator`."""

import pytest

from app.modules.pathology_interpretation_ai.domain.enums import PathologyFindingCategory
from app.modules.pathology_interpretation_ai.infrastructure.clinical_correlation.keyword_clinical_correlator import (  # noqa: E501
    KeywordClinicalCorrelator,
)


class TestExtractCandidateFindings:
    def test_returns_empty_tuple_for_text_with_no_recognized_keywords(self) -> None:
        correlator = KeywordClinicalCorrelator()
        assert correlator.extract_candidate_findings("Sections show normal architecture.") == ()

    def test_extracts_a_malignant_keyword_match(self) -> None:
        correlator = KeywordClinicalCorrelator()

        candidates = correlator.extract_candidate_findings("Sections reveal ductal carcinoma.")

        assert len(candidates) == 1
        assert candidates[0].category is PathologyFindingCategory.MALIGNANT
        assert candidates[0].description == "Carcinoma"

    def test_extracts_a_benign_keyword_match(self) -> None:
        correlator = KeywordClinicalCorrelator()

        candidates = correlator.extract_candidate_findings("Unremarkable specimen overall.")

        assert len(candidates) == 1
        assert candidates[0].category is PathologyFindingCategory.BENIGN

    def test_extracts_multiple_distinct_keyword_matches(self) -> None:
        correlator = KeywordClinicalCorrelator()

        candidates = correlator.extract_candidate_findings(
            "Findings concerning for carcinoma and lymphoma."
        )

        descriptions = {c.description for c in candidates}
        assert descriptions == {"Carcinoma", "Lymphoma"}

    def test_is_case_insensitive(self) -> None:
        correlator = KeywordClinicalCorrelator()

        candidates = correlator.extract_candidate_findings("CARCINOMA identified.")

        assert len(candidates) == 1

    @pytest.mark.parametrize(
        "keyword",
        [
            "malignant",
            "carcinoma",
            "sarcoma",
            "lymphoma",
            "melanoma",
            "metastatic",
            "metastasis",
            "invasive",
            "malignancy",
        ],
    )
    def test_recognizes_every_malignant_keyword(self, keyword: str) -> None:
        correlator = KeywordClinicalCorrelator()

        candidates = correlator.extract_candidate_findings(f"Report notes {keyword} present.")

        assert any(c.category is PathologyFindingCategory.MALIGNANT for c in candidates)

    @pytest.mark.parametrize(
        "keyword",
        [
            "benign",
            "unremarkable",
            "reactive changes",
            "within normal limits",
            "no significant abnormality",
            "normal histology",
        ],
    )
    def test_recognizes_every_benign_keyword(self, keyword: str) -> None:
        correlator = KeywordClinicalCorrelator()

        candidates = correlator.extract_candidate_findings(f"Impression: {keyword}.")

        assert any(c.category is PathologyFindingCategory.BENIGN for c in candidates)

    def test_accepts_a_custom_keyword_table(self) -> None:
        correlator = KeywordClinicalCorrelator(
            malignant_keywords=("custom malignant phrase",), benign_keywords=()
        )

        candidates = correlator.extract_candidate_findings(
            "Report mentions custom malignant phrase."
        )

        assert len(candidates) == 1
        assert candidates[0].category is PathologyFindingCategory.MALIGNANT


class TestClassifyDescription:
    def test_returns_none_for_unrecognized_text(self) -> None:
        correlator = KeywordClinicalCorrelator()
        assert correlator.classify_description("Normal architecture preserved") is None

    def test_classifies_malignant_language(self) -> None:
        correlator = KeywordClinicalCorrelator()
        assert correlator.classify_description("Consistent with sarcoma") is (
            PathologyFindingCategory.MALIGNANT
        )

    def test_classifies_benign_language(self) -> None:
        correlator = KeywordClinicalCorrelator()
        assert correlator.classify_description("Benign findings only") is (
            PathologyFindingCategory.BENIGN
        )

    def test_is_case_insensitive(self) -> None:
        correlator = KeywordClinicalCorrelator()
        assert correlator.classify_description("MELANOMA noted") is (
            PathologyFindingCategory.MALIGNANT
        )
