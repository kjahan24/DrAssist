"""Unit tests for `DifferentialDiagnosisRankingService` — this task's own
"confidence ranking" clinical-reasoning requirement."""

from app.modules.differential_diagnosis_ai.application.services.differential_diagnosis_ranking_service import (  # noqa: E501
    DifferentialDiagnosisRankingService,
)
from app.modules.differential_diagnosis_ai.domain.enums import UrgencyLevel
from tests.unit.modules.differential_diagnosis_ai.application.fakes import (
    make_candidate,
    make_result,
)


class TestDifferentialDiagnosisRankingServiceConfidenceOrdering:
    def test_higher_confidence_outranks_lower_confidence(self) -> None:
        service = DifferentialDiagnosisRankingService()
        result = make_result(
            candidates=(
                make_candidate(disease_name="Bronchitis", confidence_score=0.2),
                make_candidate(disease_name="Pneumonia", confidence_score=0.9),
            )
        )

        ranked = service.rank(result)

        assert ranked.candidates[0].disease_name == "Pneumonia"
        assert ranked.candidates[1].disease_name == "Bronchitis"

    def test_a_none_confidence_score_is_treated_as_zero(self) -> None:
        service = DifferentialDiagnosisRankingService()
        result = make_result(
            candidates=(
                make_candidate(disease_name="Unknown", confidence_score=None),
                make_candidate(disease_name="Pneumonia", confidence_score=0.1),
            )
        )

        ranked = service.rank(result)

        assert ranked.candidates[0].disease_name == "Pneumonia"


class TestDifferentialDiagnosisRankingServiceUrgencyTiebreak:
    def test_more_urgent_candidate_wins_at_equal_confidence(self) -> None:
        service = DifferentialDiagnosisRankingService()
        result = make_result(
            candidates=(
                make_candidate(
                    disease_name="Bronchitis",
                    confidence_score=0.5,
                    urgency_level=UrgencyLevel.ROUTINE,
                ),
                make_candidate(
                    disease_name="Pulmonary Embolism",
                    confidence_score=0.5,
                    urgency_level=UrgencyLevel.EMERGENT,
                ),
            )
        )

        ranked = service.rank(result)

        assert ranked.candidates[0].disease_name == "Pulmonary Embolism"


class TestDifferentialDiagnosisRankingServiceMostLikely:
    def test_most_likely_diagnosis_reflects_the_ranked_top(self) -> None:
        service = DifferentialDiagnosisRankingService()
        result = make_result(
            candidates=(
                make_candidate(disease_name="Bronchitis", confidence_score=0.2),
                make_candidate(disease_name="Pneumonia", confidence_score=0.9),
            )
        )

        ranked = service.rank(result)

        assert ranked.most_likely_diagnosis == "Pneumonia"


class TestDifferentialDiagnosisRankingServiceReturnShape:
    def test_preserves_raw_text_and_output_format(self) -> None:
        service = DifferentialDiagnosisRankingService()
        result = make_result()

        ranked = service.rank(result)

        assert ranked.raw_text == result.raw_text
        assert ranked.output_format == result.output_format

    def test_empty_result_ranks_to_empty(self) -> None:
        service = DifferentialDiagnosisRankingService()
        result = make_result(candidates=())

        ranked = service.rank(result)

        assert ranked.candidates == ()
