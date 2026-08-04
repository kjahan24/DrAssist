"""Unit tests for `DefaultICD10SuggestionValidator`."""

import pytest

from app.modules.icd10_ai.domain.exceptions import (
    DuplicateICD10CodeError,
    EmptyICD10ResponseError,
    HallucinatedDiagnosisError,
    InvalidICD10CodeError,
    MissingConfidenceScoreError,
)
from app.modules.icd10_ai.infrastructure.validation.icd10_suggestion_validator import (
    DefaultICD10SuggestionValidator,
)
from tests.unit.modules.icd10_ai.application.fakes import (
    FakeICD10KnowledgePort,
    make_suggestion,
    make_suggestion_set,
)


class TestValidateHappyPath:
    def test_accepts_a_well_formed_suggestion_set(self) -> None:
        validator = DefaultICD10SuggestionValidator(knowledge=FakeICD10KnowledgePort())
        validator.validate(make_suggestion_set())


class TestValidateEmptyResponse:
    def test_raises_when_there_are_no_suggestions(self) -> None:
        validator = DefaultICD10SuggestionValidator(knowledge=FakeICD10KnowledgePort())
        suggestion_set = make_suggestion_set(suggestions=())

        with pytest.raises(EmptyICD10ResponseError):
            validator.validate(suggestion_set)


class TestValidateInvalidCodes:
    def test_raises_when_a_code_fails_format_validation(self) -> None:
        knowledge = FakeICD10KnowledgePort(valid_format_codes=set())
        validator = DefaultICD10SuggestionValidator(knowledge=knowledge)
        suggestion_set = make_suggestion_set(suggestions=(make_suggestion(icd10_code="NOTACODE"),))

        with pytest.raises(InvalidICD10CodeError) as exc_info:
            validator.validate(suggestion_set)
        assert exc_info.value.icd10_code == "NOTACODE"

    def test_accepts_a_code_that_passes_format_validation(self) -> None:
        knowledge = FakeICD10KnowledgePort(valid_format_codes={"J06.9"})
        validator = DefaultICD10SuggestionValidator(knowledge=knowledge)
        suggestion_set = make_suggestion_set(suggestions=(make_suggestion(icd10_code="J06.9"),))

        validator.validate(suggestion_set)


class TestValidateDuplicateCodes:
    def test_raises_when_the_same_code_appears_twice(self) -> None:
        validator = DefaultICD10SuggestionValidator(knowledge=FakeICD10KnowledgePort())
        suggestion_set = make_suggestion_set(
            suggestions=(
                make_suggestion(icd10_code="J06.9"),
                make_suggestion(icd10_code="J06.9"),
            )
        )

        with pytest.raises(DuplicateICD10CodeError) as exc_info:
            validator.validate(suggestion_set)
        assert exc_info.value.icd10_code == "J06.9"

    def test_duplicate_detection_is_case_and_whitespace_insensitive(self) -> None:
        validator = DefaultICD10SuggestionValidator(knowledge=FakeICD10KnowledgePort())
        suggestion_set = make_suggestion_set(
            suggestions=(
                make_suggestion(icd10_code="j06.9"),
                make_suggestion(icd10_code="  J06.9  "),
            )
        )

        with pytest.raises(DuplicateICD10CodeError):
            validator.validate(suggestion_set)

    def test_does_not_flag_genuinely_different_codes(self) -> None:
        validator = DefaultICD10SuggestionValidator(knowledge=FakeICD10KnowledgePort())
        suggestion_set = make_suggestion_set(
            suggestions=(
                make_suggestion(icd10_code="J06.9"),
                make_suggestion(icd10_code="R50.9"),
            )
        )

        validator.validate(suggestion_set)


class TestValidateHallucinatedDiagnoses:
    @pytest.mark.parametrize(
        "placeholder",
        [
            "[insert diagnosis here]",
            "[PLACEHOLDER]",
            "<insert findings>",
            "TBD",
            "TODO",
            "XXX",
            "Lorem ipsum dolor sit amet",
        ],
    )
    def test_raises_when_diagnosis_name_contains_a_placeholder(self, placeholder: str) -> None:
        validator = DefaultICD10SuggestionValidator(knowledge=FakeICD10KnowledgePort())
        suggestion_set = make_suggestion_set(
            suggestions=(make_suggestion(diagnosis_name=f"Diagnosis: {placeholder}"),)
        )

        with pytest.raises(HallucinatedDiagnosisError) as exc_info:
            validator.validate(suggestion_set)
        assert exc_info.value.icd10_code == "J06.9"

    def test_raises_when_clinical_reasoning_contains_a_placeholder(self) -> None:
        validator = DefaultICD10SuggestionValidator(knowledge=FakeICD10KnowledgePort())
        suggestion_set = make_suggestion_set(
            suggestions=(make_suggestion(clinical_reasoning="Reasoning: TBD"),)
        )

        with pytest.raises(HallucinatedDiagnosisError):
            validator.validate(suggestion_set)

    def test_raises_when_supporting_evidence_contains_a_placeholder(self) -> None:
        validator = DefaultICD10SuggestionValidator(knowledge=FakeICD10KnowledgePort())
        suggestion_set = make_suggestion_set(
            suggestions=(make_suggestion(supporting_evidence="[insert evidence]"),)
        )

        with pytest.raises(HallucinatedDiagnosisError):
            validator.validate(suggestion_set)

    def test_does_not_flag_ordinary_clinical_language(self) -> None:
        validator = DefaultICD10SuggestionValidator(knowledge=FakeICD10KnowledgePort())
        validator.validate(make_suggestion_set())


class TestValidateMissingConfidenceScore:
    def test_raises_when_confidence_score_is_none(self) -> None:
        validator = DefaultICD10SuggestionValidator(knowledge=FakeICD10KnowledgePort())
        suggestion_set = make_suggestion_set(suggestions=(make_suggestion(confidence_score=None),))

        with pytest.raises(MissingConfidenceScoreError) as exc_info:
            validator.validate(suggestion_set)
        assert exc_info.value.icd10_code == "J06.9"

    @pytest.mark.parametrize("confidence_score", [-0.1, 1.1, -5.0, 100.0])
    def test_raises_when_confidence_score_is_out_of_range(self, confidence_score: float) -> None:
        validator = DefaultICD10SuggestionValidator(knowledge=FakeICD10KnowledgePort())
        suggestion_set = make_suggestion_set(
            suggestions=(make_suggestion(confidence_score=confidence_score),)
        )

        with pytest.raises(MissingConfidenceScoreError):
            validator.validate(suggestion_set)

    @pytest.mark.parametrize("confidence_score", [0.0, 1.0, 0.5])
    def test_accepts_boundary_valid_confidence_scores(self, confidence_score: float) -> None:
        validator = DefaultICD10SuggestionValidator(knowledge=FakeICD10KnowledgePort())
        suggestion_set = make_suggestion_set(
            suggestions=(make_suggestion(confidence_score=confidence_score),)
        )

        validator.validate(suggestion_set)


class TestValidateCheckOrdering:
    def test_empty_response_is_checked_before_per_suggestion_checks(self) -> None:
        """An empty suggestion set never reaches the knowledge port —
        confirms `EmptyICD10ResponseError` is the very first check."""
        knowledge = FakeICD10KnowledgePort()
        validator = DefaultICD10SuggestionValidator(knowledge=knowledge)

        with pytest.raises(EmptyICD10ResponseError):
            validator.validate(make_suggestion_set(suggestions=()))

        assert knowledge.format_checks == []
