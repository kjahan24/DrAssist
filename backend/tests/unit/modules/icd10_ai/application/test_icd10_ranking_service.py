"""Unit tests for `ICD10RankingService` — this task's own "RANKING — Rank
diagnoses using: confidence, supporting evidence, clinical relevance"
requirement."""

from app.modules.icd10_ai.application.services.icd10_ranking_service import ICD10RankingService
from app.modules.icd10_ai.domain.enums import DiagnosisFlag
from tests.unit.modules.icd10_ai.application.fakes import (
    FakeICD10KnowledgePort,
    make_suggestion,
    make_suggestion_set,
)


class TestICD10RankingServicePrimaryFlagDominance:
    def test_primary_flagged_suggestion_always_outranks_secondary(self) -> None:
        service = ICD10RankingService(knowledge=FakeICD10KnowledgePort())
        suggestion_set = make_suggestion_set(
            suggestions=(
                make_suggestion(
                    icd10_code="A00", flag=DiagnosisFlag.SECONDARY, confidence_score=0.99
                ),
                make_suggestion(
                    icd10_code="B00", flag=DiagnosisFlag.PRIMARY, confidence_score=0.10
                ),
            )
        )

        ranked = service.rank(suggestion_set)

        assert ranked.suggestions[0].icd10_code == "B00"
        assert ranked.suggestions[1].icd10_code == "A00"


class TestICD10RankingServiceConfidenceOrdering:
    def test_higher_confidence_outranks_lower_confidence_within_the_same_flag(self) -> None:
        service = ICD10RankingService(knowledge=FakeICD10KnowledgePort())
        suggestion_set = make_suggestion_set(
            suggestions=(
                make_suggestion(
                    icd10_code="A00", flag=DiagnosisFlag.SECONDARY, confidence_score=0.2
                ),
                make_suggestion(
                    icd10_code="B00", flag=DiagnosisFlag.SECONDARY, confidence_score=0.8
                ),
            )
        )

        ranked = service.rank(suggestion_set)

        assert ranked.suggestions[0].icd10_code == "B00"
        assert ranked.suggestions[1].icd10_code == "A00"

    def test_a_none_confidence_score_is_treated_as_zero(self) -> None:
        service = ICD10RankingService(knowledge=FakeICD10KnowledgePort())
        suggestion_set = make_suggestion_set(
            suggestions=(
                make_suggestion(
                    icd10_code="A00", flag=DiagnosisFlag.SECONDARY, confidence_score=None
                ),
                make_suggestion(
                    icd10_code="B00", flag=DiagnosisFlag.SECONDARY, confidence_score=0.1
                ),
            )
        )

        ranked = service.rank(suggestion_set)

        assert ranked.suggestions[0].icd10_code == "B00"


class TestICD10RankingServiceSupportingEvidence:
    def test_non_blank_supporting_evidence_outranks_blank_at_equal_confidence(self) -> None:
        service = ICD10RankingService(knowledge=FakeICD10KnowledgePort())
        suggestion_set = make_suggestion_set(
            suggestions=(
                make_suggestion(
                    icd10_code="A00",
                    flag=DiagnosisFlag.SECONDARY,
                    confidence_score=0.5,
                    supporting_evidence="",
                ),
                make_suggestion(
                    icd10_code="B00",
                    flag=DiagnosisFlag.SECONDARY,
                    confidence_score=0.5,
                    supporting_evidence="fever, sore throat",
                ),
            )
        )

        ranked = service.rank(suggestion_set)

        assert ranked.suggestions[0].icd10_code == "B00"


class TestICD10RankingServiceClinicalRelevance:
    def test_a_recognized_common_code_outranks_an_unrecognized_one_at_equal_confidence(
        self,
    ) -> None:
        knowledge = FakeICD10KnowledgePort(canonical_names={"J06.9": "Acute URI, unspecified"})
        service = ICD10RankingService(knowledge=knowledge)
        suggestion_set = make_suggestion_set(
            suggestions=(
                make_suggestion(
                    icd10_code="Z99.9",
                    flag=DiagnosisFlag.SECONDARY,
                    confidence_score=0.5,
                    supporting_evidence="x",
                ),
                make_suggestion(
                    icd10_code="J06.9",
                    flag=DiagnosisFlag.SECONDARY,
                    confidence_score=0.5,
                    supporting_evidence="x",
                ),
            )
        )

        ranked = service.rank(suggestion_set)

        assert ranked.suggestions[0].icd10_code == "J06.9"

    def test_an_unrecognized_code_is_not_scored_to_zero_relevance(self) -> None:
        """An empty curated reference set must not zero out ranking —
        `lookup_canonical_name` returning `None` means "not in the
        curated set", not "irrelevant" (see the service's own module
        docstring)."""
        knowledge = FakeICD10KnowledgePort(canonical_names={})
        service = ICD10RankingService(knowledge=knowledge)
        suggestion_set = make_suggestion_set(
            suggestions=(make_suggestion(icd10_code="Z99.9", confidence_score=0.9),)
        )

        ranked = service.rank(suggestion_set)

        assert ranked.suggestions[0].icd10_code == "Z99.9"


class TestICD10RankingServiceReturnShape:
    def test_preserves_raw_text_and_output_format(self) -> None:
        service = ICD10RankingService(knowledge=FakeICD10KnowledgePort())
        suggestion_set = make_suggestion_set()

        ranked = service.rank(suggestion_set)

        assert ranked.raw_text == suggestion_set.raw_text
        assert ranked.output_format == suggestion_set.output_format

    def test_empty_suggestion_set_ranks_to_empty(self) -> None:
        service = ICD10RankingService(knowledge=FakeICD10KnowledgePort())
        suggestion_set = make_suggestion_set(suggestions=())

        ranked = service.rank(suggestion_set)

        assert ranked.suggestions == ()
