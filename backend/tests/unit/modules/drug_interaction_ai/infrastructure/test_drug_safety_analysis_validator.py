"""Unit tests for `DefaultDrugSafetyAnalysisValidator`."""

from uuid import uuid4

import pytest

from app.modules.drug_interaction_ai.domain.enums import (
    DrugInteractionSetting,
    EvidenceLevel,
    SafetySeverity,
)
from app.modules.drug_interaction_ai.domain.exceptions import (
    HallucinatedInteractionError,
    InvalidDrugInteractionConfidenceValueError,
    MissingInteractionEvidenceError,
    UnknownMedicationError,
)
from app.modules.drug_interaction_ai.domain.value_objects import DrugInteractionAnalysisInput
from app.modules.drug_interaction_ai.infrastructure.validation.drug_safety_analysis_validator import (  # noqa: E501
    DefaultDrugSafetyAnalysisValidator,
)
from tests.unit.modules.drug_interaction_ai.application.fakes import (
    make_issue,
    make_medication,
    make_result,
)


def _input(**overrides: object) -> DrugInteractionAnalysisInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "medication_setting": DrugInteractionSetting.OUTPATIENT,
        "current_medications": (
            make_medication(drug_name="Warfarin"),
            make_medication(drug_name="Aspirin"),
        ),
    }
    defaults.update(overrides)
    return DrugInteractionAnalysisInput(**defaults)  # type: ignore[arg-type]


def _validator() -> DefaultDrugSafetyAnalysisValidator:
    return DefaultDrugSafetyAnalysisValidator()


class TestValidateHappyPath:
    def test_accepts_a_well_formed_result(self) -> None:
        _validator().validate(make_result(), _input())


class TestValidateUnknownMedications:
    def test_raises_when_an_involved_medication_was_never_supplied(self) -> None:
        result = make_result(
            interactions=(make_issue(involved_medications=("Ibuprofen", "Aspirin")),)
        )

        with pytest.raises(UnknownMedicationError) as exc_info:
            _validator().validate(result, _input())
        assert exc_info.value.medication_name == "Ibuprofen"

    def test_accepts_medications_that_were_supplied(self) -> None:
        result = make_result(
            interactions=(make_issue(involved_medications=("Warfarin", "Aspirin")),)
        )
        _validator().validate(result, _input())

    def test_matches_case_insensitively(self) -> None:
        result = make_result(interactions=(make_issue(involved_medications=("WARFARIN",)),))
        _validator().validate(result, _input())

    def test_matches_by_substring_to_tolerate_dose_suffixes(self) -> None:
        result = make_result(interactions=(make_issue(involved_medications=("Warfarin 5mg",)),))
        _validator().validate(result, _input())

    def test_matches_against_generic_name(self) -> None:
        result = make_result(interactions=(make_issue(involved_medications=("Coumadin",)),))
        input_dto = _input(
            current_medications=(make_medication(drug_name="Warfarin", generic_name="Coumadin"),)
        )
        _validator().validate(result, input_dto)

    def test_matches_against_new_prescription(self) -> None:
        result = make_result(interactions=(make_issue(involved_medications=("Ibuprofen",)),))
        input_dto = _input(
            current_medications=(),
            new_prescription=make_medication(drug_name="Ibuprofen"),
        )
        _validator().validate(result, input_dto)

    def test_accepts_an_empty_involved_medications_list(self) -> None:
        result = make_result(interactions=(make_issue(involved_medications=()),))
        _validator().validate(result, _input())


class TestValidateInvalidConfidenceValues:
    @pytest.mark.parametrize("confidence_score", [-0.1, 1.1, -5.0, 100.0])
    def test_raises_when_confidence_is_out_of_range(self, confidence_score: float) -> None:
        result = make_result(confidence_score=confidence_score)

        with pytest.raises(InvalidDrugInteractionConfidenceValueError):
            _validator().validate(result, _input())

    def test_accepts_a_none_confidence_value(self) -> None:
        result = make_result(confidence_score=None)
        _validator().validate(result, _input())

    @pytest.mark.parametrize("confidence_score", [0.0, 1.0, 0.5])
    def test_accepts_boundary_valid_confidence_scores(self, confidence_score: float) -> None:
        result = make_result(confidence_score=confidence_score)
        _validator().validate(result, _input())


class TestValidateMissingEvidence:
    def test_raises_when_a_major_interaction_has_no_evidence_level(self) -> None:
        result = make_result(
            interactions=(
                make_issue(
                    severity=SafetySeverity.MAJOR,
                    evidence_level=None,
                    involved_medications=("Warfarin",),
                ),
            )
        )

        with pytest.raises(MissingInteractionEvidenceError):
            _validator().validate(result, _input())

    def test_raises_when_a_contraindicated_interaction_has_no_evidence_level(self) -> None:
        result = make_result(
            interactions=(
                make_issue(
                    severity=SafetySeverity.CONTRAINDICATED,
                    evidence_level=None,
                    involved_medications=("Warfarin",),
                ),
            )
        )

        with pytest.raises(MissingInteractionEvidenceError):
            _validator().validate(result, _input())

    def test_accepts_a_minor_interaction_with_no_evidence_level(self) -> None:
        result = make_result(
            interactions=(
                make_issue(
                    severity=SafetySeverity.MINOR,
                    evidence_level=None,
                    involved_medications=("Warfarin",),
                ),
            )
        )
        _validator().validate(result, _input())

    def test_accepts_a_moderate_interaction_with_no_evidence_level(self) -> None:
        result = make_result(
            interactions=(
                make_issue(
                    severity=SafetySeverity.MODERATE,
                    evidence_level=None,
                    involved_medications=("Warfarin",),
                ),
            )
        )
        _validator().validate(result, _input())

    def test_accepts_a_major_interaction_with_an_evidence_level(self) -> None:
        result = make_result(
            interactions=(
                make_issue(
                    severity=SafetySeverity.MAJOR,
                    evidence_level=EvidenceLevel.PROBABLE,
                    involved_medications=("Warfarin",),
                ),
            )
        )
        _validator().validate(result, _input())


class TestValidateHallucinatedPlaceholders:
    @pytest.mark.parametrize(
        "placeholder",
        [
            "[insert summary here]",
            "[PLACEHOLDER]",
            "<insert findings>",
            "TBD",
            "TODO",
            "XXX",
            "Lorem ipsum dolor sit amet",
        ],
    )
    def test_raises_when_safety_summary_contains_a_placeholder(self, placeholder: str) -> None:
        result = make_result(safety_summary=f"Summary: {placeholder}")

        with pytest.raises(HallucinatedInteractionError) as exc_info:
            _validator().validate(result, _input())
        assert exc_info.value.field_name == "safety_summary"

    def test_raises_when_clinical_reasoning_contains_a_placeholder(self) -> None:
        result = make_result(clinical_reasoning="Reasoning: TBD")

        with pytest.raises(HallucinatedInteractionError):
            _validator().validate(result, _input())

    def test_raises_when_an_interaction_description_contains_a_placeholder(self) -> None:
        result = make_result(interactions=(make_issue(description="[insert interaction]"),))

        with pytest.raises(HallucinatedInteractionError) as exc_info:
            _validator().validate(result, _input())
        assert exc_info.value.field_name == "interactions"

    def test_raises_when_an_interaction_mechanism_contains_a_placeholder(self) -> None:
        result = make_result(interactions=(make_issue(mechanism="TBD"),))

        with pytest.raises(HallucinatedInteractionError):
            _validator().validate(result, _input())

    def test_raises_when_a_contraindication_contains_a_placeholder(self) -> None:
        result = make_result(contraindications=("[insert contraindication]",))

        with pytest.raises(HallucinatedInteractionError) as exc_info:
            _validator().validate(result, _input())
        assert exc_info.value.field_name == "contraindications"

    def test_raises_when_a_patient_counseling_point_contains_a_placeholder(self) -> None:
        result = make_result(patient_counseling_points=("TBD",))

        with pytest.raises(HallucinatedInteractionError) as exc_info:
            _validator().validate(result, _input())
        assert exc_info.value.field_name == "patient_counseling_points"

    def test_does_not_flag_ordinary_clinical_language(self) -> None:
        _validator().validate(make_result(), _input())


class TestValidateCheckOrdering:
    def test_unknown_medication_is_checked_before_confidence_value(self) -> None:
        result = make_result(
            interactions=(make_issue(involved_medications=("Ibuprofen",)),),
            confidence_score=5.0,
        )

        with pytest.raises(UnknownMedicationError):
            _validator().validate(result, _input())
