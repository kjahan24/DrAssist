"""Unit tests for `DefaultDifferentialDiagnosisValidator`."""

import pytest

from app.modules.differential_diagnosis_ai.domain.exceptions import (
    DuplicateDiagnosisError,
    EmptyDifferentialResponseError,
    HallucinatedDiagnosisError,
    InconsistentReasoningError,
    InvalidConfidenceScoreError,
    InvalidRankingError,
)
from app.modules.differential_diagnosis_ai.infrastructure.validation.differential_diagnosis_validator import (  # noqa: E501
    DefaultDifferentialDiagnosisValidator,
)
from tests.unit.modules.differential_diagnosis_ai.application.fakes import (
    make_candidate,
    make_result,
)


class TestValidateHappyPath:
    def test_accepts_a_well_formed_result(self) -> None:
        validator = DefaultDifferentialDiagnosisValidator()
        validator.validate(make_result())


class TestValidateEmptyResponse:
    def test_raises_when_there_are_no_candidates(self) -> None:
        validator = DefaultDifferentialDiagnosisValidator()
        result = make_result(candidates=())

        with pytest.raises(EmptyDifferentialResponseError):
            validator.validate(result)


class TestValidateDuplicateDiagnoses:
    def test_raises_when_the_same_disease_name_appears_twice(self) -> None:
        validator = DefaultDifferentialDiagnosisValidator()
        result = make_result(
            candidates=(
                make_candidate(disease_name="Pneumonia", confidence_score=0.9),
                make_candidate(disease_name="Pneumonia", confidence_score=0.5),
            )
        )

        with pytest.raises(DuplicateDiagnosisError) as exc_info:
            validator.validate(result)
        assert exc_info.value.disease_name == "Pneumonia"

    def test_duplicate_detection_is_case_and_whitespace_insensitive(self) -> None:
        validator = DefaultDifferentialDiagnosisValidator()
        result = make_result(
            candidates=(
                make_candidate(disease_name="Pneumonia", confidence_score=0.9),
                make_candidate(disease_name="  pneumonia  ", confidence_score=0.5),
            )
        )

        with pytest.raises(DuplicateDiagnosisError):
            validator.validate(result)

    def test_does_not_flag_genuinely_different_diagnoses(self) -> None:
        validator = DefaultDifferentialDiagnosisValidator()
        result = make_result(
            candidates=(
                make_candidate(disease_name="Pneumonia", confidence_score=0.9),
                make_candidate(disease_name="Bronchitis", confidence_score=0.5),
            )
        )

        validator.validate(result)


class TestValidateInvalidConfidenceScore:
    def test_raises_when_confidence_score_is_none(self) -> None:
        validator = DefaultDifferentialDiagnosisValidator()
        result = make_result(candidates=(make_candidate(confidence_score=None),))

        with pytest.raises(InvalidConfidenceScoreError) as exc_info:
            validator.validate(result)
        assert exc_info.value.disease_name == "Pneumonia"

    @pytest.mark.parametrize("confidence_score", [-0.1, 1.1, -5.0, 100.0])
    def test_raises_when_confidence_score_is_out_of_range(self, confidence_score: float) -> None:
        validator = DefaultDifferentialDiagnosisValidator()
        result = make_result(candidates=(make_candidate(confidence_score=confidence_score),))

        with pytest.raises(InvalidConfidenceScoreError):
            validator.validate(result)

    @pytest.mark.parametrize("confidence_score", [0.0, 1.0, 0.5])
    def test_accepts_boundary_valid_confidence_scores(self, confidence_score: float) -> None:
        validator = DefaultDifferentialDiagnosisValidator()
        result = make_result(candidates=(make_candidate(confidence_score=confidence_score),))

        validator.validate(result)


class TestValidateInvalidRanking:
    def test_raises_when_candidates_are_out_of_confidence_order(self) -> None:
        validator = DefaultDifferentialDiagnosisValidator()
        result = make_result(
            candidates=(
                make_candidate(disease_name="Bronchitis", confidence_score=0.2),
                make_candidate(disease_name="Pneumonia", confidence_score=0.9),
            )
        )

        with pytest.raises(InvalidRankingError):
            validator.validate(result)

    def test_accepts_non_increasing_order(self) -> None:
        validator = DefaultDifferentialDiagnosisValidator()
        result = make_result(
            candidates=(
                make_candidate(disease_name="Pneumonia", confidence_score=0.9),
                make_candidate(disease_name="Bronchitis", confidence_score=0.2),
            )
        )

        validator.validate(result)

    def test_accepts_equal_consecutive_confidence_scores(self) -> None:
        validator = DefaultDifferentialDiagnosisValidator()
        result = make_result(
            candidates=(
                make_candidate(disease_name="Pneumonia", confidence_score=0.5),
                make_candidate(disease_name="Bronchitis", confidence_score=0.5),
            )
        )

        validator.validate(result)


class TestValidateHallucinatedDiagnoses:
    @pytest.mark.parametrize(
        "placeholder",
        [
            "[insert reasoning here]",
            "[PLACEHOLDER]",
            "<insert findings>",
            "TBD",
            "TODO",
            "XXX",
            "Lorem ipsum dolor sit amet",
        ],
    )
    def test_raises_when_clinical_reasoning_contains_a_placeholder(self, placeholder: str) -> None:
        validator = DefaultDifferentialDiagnosisValidator()
        result = make_result(
            candidates=(make_candidate(clinical_reasoning=f"Reasoning: {placeholder}"),)
        )

        with pytest.raises(HallucinatedDiagnosisError) as exc_info:
            validator.validate(result)
        assert exc_info.value.disease_name == "Pneumonia"

    def test_raises_when_disease_name_contains_a_placeholder(self) -> None:
        validator = DefaultDifferentialDiagnosisValidator()
        result = make_result(candidates=(make_candidate(disease_name="[INSERT DIAGNOSIS]"),))

        with pytest.raises(HallucinatedDiagnosisError):
            validator.validate(result)

    def test_raises_when_a_supporting_finding_contains_a_placeholder(self) -> None:
        validator = DefaultDifferentialDiagnosisValidator()
        result = make_result(
            candidates=(make_candidate(supporting_findings=("[insert finding]",)),)
        )

        with pytest.raises(HallucinatedDiagnosisError):
            validator.validate(result)

    def test_raises_when_a_recommended_next_test_contains_a_placeholder(self) -> None:
        validator = DefaultDifferentialDiagnosisValidator()
        result = make_result(candidates=(make_candidate(recommended_next_tests=("TBD",)),))

        with pytest.raises(HallucinatedDiagnosisError):
            validator.validate(result)

    def test_does_not_flag_ordinary_clinical_language(self) -> None:
        validator = DefaultDifferentialDiagnosisValidator()
        validator.validate(make_result())


class TestValidateInconsistentReasoning:
    def test_raises_when_a_finding_appears_in_both_supporting_and_against(self) -> None:
        validator = DefaultDifferentialDiagnosisValidator()
        result = make_result(
            candidates=(
                make_candidate(
                    supporting_findings=("fever",),
                    findings_against=("fever",),
                ),
            )
        )

        with pytest.raises(InconsistentReasoningError) as exc_info:
            validator.validate(result)
        assert exc_info.value.disease_name == "Pneumonia"

    def test_overlap_detection_is_case_and_whitespace_insensitive(self) -> None:
        validator = DefaultDifferentialDiagnosisValidator()
        result = make_result(
            candidates=(
                make_candidate(
                    supporting_findings=("Fever",),
                    findings_against=("  fever  ",),
                ),
            )
        )

        with pytest.raises(InconsistentReasoningError):
            validator.validate(result)

    def test_does_not_flag_genuinely_different_findings(self) -> None:
        validator = DefaultDifferentialDiagnosisValidator()
        result = make_result(
            candidates=(
                make_candidate(
                    supporting_findings=("fever", "cough"),
                    findings_against=("no consolidation",),
                ),
            )
        )

        validator.validate(result)


class TestValidateCheckOrdering:
    def test_confidence_is_checked_before_ranking(self) -> None:
        """A candidate with an invalid confidence score must raise
        `InvalidConfidenceScoreError`, not `InvalidRankingError`, even
        when the candidate order would also look wrong — confirms
        confidence validity is checked first."""
        validator = DefaultDifferentialDiagnosisValidator()
        result = make_result(
            candidates=(
                make_candidate(disease_name="A", confidence_score=None),
                make_candidate(disease_name="B", confidence_score=0.9),
            )
        )

        with pytest.raises(InvalidConfidenceScoreError):
            validator.validate(result)
