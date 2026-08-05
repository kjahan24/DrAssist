"""Unit tests for the AI Drug Interaction & Medication Safety module's
domain value objects."""

from uuid import uuid4

import pytest

from app.modules.drug_interaction_ai.domain.enums import (
    DrugInteractionOutputFormat,
    DrugInteractionSetting,
    EvidenceLevel,
    SafetyIssueCategory,
    SafetySeverity,
)
from app.modules.drug_interaction_ai.domain.exceptions import (
    DuplicateMedicationError,
    EmptyMedicationListError,
    InvalidDrugInteractionInputError,
)
from app.modules.drug_interaction_ai.domain.value_objects import (
    DrugInteractionAnalysisInput,
    DrugInteractionAnalysisResult,
    MedicationEntry,
    SafetyIssue,
)


def _medication(**overrides: object) -> MedicationEntry:
    defaults: dict[str, object] = {"drug_name": "Warfarin"}
    defaults.update(overrides)
    return MedicationEntry(**defaults)  # type: ignore[arg-type]


def _input(**overrides: object) -> DrugInteractionAnalysisInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "medication_setting": DrugInteractionSetting.OUTPATIENT,
        "current_medications": (_medication(),),
    }
    defaults.update(overrides)
    return DrugInteractionAnalysisInput(**defaults)  # type: ignore[arg-type]


class TestMedicationEntry:
    def test_accepts_a_well_formed_medication(self) -> None:
        medication = _medication(drug_name="Aspirin", dose="81mg", frequency="once daily")
        assert medication.drug_name == "Aspirin"
        assert medication.dose == "81mg"

    def test_raises_when_drug_name_is_blank(self) -> None:
        with pytest.raises(InvalidDrugInteractionInputError):
            _medication(drug_name="   ")

    def test_optional_fields_default_to_none(self) -> None:
        medication = _medication()
        assert medication.generic_name is None
        assert medication.brand_name is None
        assert medication.dose is None
        assert medication.frequency is None
        assert medication.route is None
        assert medication.duration is None


class TestDrugInteractionAnalysisInput:
    def test_accepts_a_well_formed_input_with_current_medications_only(self) -> None:
        _input()

    def test_accepts_a_well_formed_input_with_new_prescription_only(self) -> None:
        _input(current_medications=(), new_prescription=_medication(drug_name="Ibuprofen"))

    def test_raises_when_both_current_medications_and_new_prescription_are_absent(self) -> None:
        with pytest.raises(EmptyMedicationListError):
            _input(current_medications=(), new_prescription=None)

    def test_raises_when_language_is_blank(self) -> None:
        with pytest.raises(InvalidDrugInteractionInputError):
            _input(language="   ")

    @pytest.mark.parametrize("patient_age", [-1, 151])
    def test_raises_when_patient_age_is_out_of_range(self, patient_age: int) -> None:
        with pytest.raises(InvalidDrugInteractionInputError):
            _input(patient_age=patient_age)

    @pytest.mark.parametrize("patient_age", [0, 150, 42])
    def test_accepts_boundary_patient_ages(self, patient_age: int) -> None:
        _input(patient_age=patient_age)

    def test_accepts_a_missing_patient_age(self) -> None:
        _input(patient_age=None)

    @pytest.mark.parametrize("weight", [0.0, -5.0])
    def test_raises_when_patient_weight_kg_is_not_positive(self, weight: float) -> None:
        with pytest.raises(InvalidDrugInteractionInputError):
            _input(patient_weight_kg=weight)

    def test_accepts_a_positive_patient_weight_kg(self) -> None:
        _input(patient_weight_kg=70.5)

    def test_accepts_a_missing_patient_weight_kg(self) -> None:
        _input(patient_weight_kg=None)

    def test_raises_on_an_exact_duplicate_medication_in_current_medications(self) -> None:
        with pytest.raises(DuplicateMedicationError) as exc_info:
            _input(current_medications=(_medication(), _medication()))
        assert exc_info.value.drug_name == "Warfarin"

    def test_allows_two_medications_with_different_doses(self) -> None:
        _input(
            current_medications=(
                _medication(dose="5mg"),
                _medication(dose="10mg"),
            )
        )

    def test_allows_two_different_drug_names(self) -> None:
        _input(
            current_medications=(
                _medication(drug_name="Warfarin"),
                _medication(drug_name="Aspirin"),
            )
        )

    def test_does_not_flag_new_prescription_as_a_duplicate_of_current_medications(self) -> None:
        _input(
            current_medications=(_medication(drug_name="Warfarin"),),
            new_prescription=_medication(drug_name="Warfarin"),
        )

    def test_carries_through_medication_setting(self) -> None:
        input_dto = _input(medication_setting=DrugInteractionSetting.PREGNANCY)
        assert input_dto.medication_setting is DrugInteractionSetting.PREGNANCY

    def test_no_visit_context_or_sibling_ai_fields_exist(self) -> None:
        """This task's own SUPPORTED INPUT section names no visit
        context, clinical notes, or sibling-AI-module context fields —
        see `domain/value_objects.py`'s own module docstring."""
        field_names = set(DrugInteractionAnalysisInput.__dataclass_fields__)
        assert "visit_id" not in field_names
        assert "clinical_notes" not in field_names
        assert "soap_notes" not in field_names


class TestSafetyIssue:
    def test_carries_its_fields(self) -> None:
        issue = SafetyIssue(
            category=SafetyIssueCategory.DRUG_DRUG_INTERACTION,
            description="Bleeding risk",
            severity=SafetySeverity.MAJOR,
            mechanism="Additive anticoagulation",
            clinical_significance="Increased bleeding risk",
            evidence_level=EvidenceLevel.ESTABLISHED,
            involved_medications=("Warfarin", "Aspirin"),
        )
        assert issue.category is SafetyIssueCategory.DRUG_DRUG_INTERACTION
        assert issue.involved_medications == ("Warfarin", "Aspirin")

    def test_optional_fields_default_appropriately(self) -> None:
        issue = SafetyIssue(
            category=SafetyIssueCategory.CONTRAINDICATION,
            description="x",
            severity=SafetySeverity.MINOR,
        )
        assert issue.mechanism is None
        assert issue.clinical_significance is None
        assert issue.evidence_level is None
        assert issue.involved_medications == ()


class TestDrugInteractionAnalysisResult:
    def _result(self, **overrides: object) -> DrugInteractionAnalysisResult:
        defaults: dict[str, object] = {
            "safety_summary": "Reviewed.",
            "interactions": (),
            "contraindications": (),
            "warnings": (),
            "monitoring_recommendations": (),
            "dose_adjustment_suggestions": (),
            "alternative_medication_suggestions": (),
            "patient_counseling_points": (),
            "clinical_reasoning": "Grounded in the medication list.",
            "confidence_score": 0.7,
            "raw_text": "{}",
            "output_format": DrugInteractionOutputFormat.JSON,
        }
        defaults.update(overrides)
        return DrugInteractionAnalysisResult(**defaults)  # type: ignore[arg-type]

    def test_is_empty_true_when_every_field_is_vacuous(self) -> None:
        result = self._result(safety_summary="", clinical_reasoning="")
        assert result.is_empty is True

    def test_is_empty_false_when_safety_summary_is_present(self) -> None:
        result = self._result(clinical_reasoning="")
        assert result.is_empty is False

    def test_is_empty_false_when_interactions_present(self) -> None:
        result = self._result(
            safety_summary="",
            clinical_reasoning="",
            interactions=(
                SafetyIssue(
                    category=SafetyIssueCategory.DRUG_DRUG_INTERACTION,
                    description="x",
                    severity=SafetySeverity.MINOR,
                ),
            ),
        )
        assert result.is_empty is False
