"""Unit tests for the AI Prescription Assistance module's domain enums."""

from app.modules.prescription_ai.domain.enums import (
    AdministrationRoute,
    GenerationStatus,
    PatientSex,
    PregnancyStatus,
    PrescribingSetting,
    PrescriptionOutputFormat,
    SafetyFindingCategory,
    SafetySeverity,
)


class TestPrescribingSetting:
    def test_has_exactly_six_members(self) -> None:
        assert {member.value for member in PrescribingSetting} == {
            "outpatient",
            "emergency",
            "inpatient",
            "pediatric",
            "geriatric",
            "follow_up",
        }

    def test_is_constructible_from_its_string_value(self) -> None:
        assert PrescribingSetting("pediatric") is PrescribingSetting.PEDIATRIC


class TestPrescriptionOutputFormat:
    def test_has_exactly_three_members(self) -> None:
        assert {member.value for member in PrescriptionOutputFormat} == {
            "json",
            "markdown",
            "text",
        }


class TestAdministrationRoute:
    def test_has_exactly_twelve_members(self) -> None:
        assert {member.value for member in AdministrationRoute} == {
            "oral",
            "iv",
            "im",
            "sc",
            "topical",
            "inhalation",
            "ophthalmic",
            "otic",
            "nasal",
            "rectal",
            "vaginal",
            "other",
        }


class TestSafetyFindingCategory:
    def test_has_exactly_nine_members(self) -> None:
        assert {member.value for member in SafetyFindingCategory} == {
            "allergy_conflict",
            "duplicate_therapy",
            "contraindication",
            "drug_interaction",
            "pregnancy_risk",
            "pediatric_dosing",
            "geriatric_precaution",
            "renal_precaution",
            "hepatic_precaution",
        }


class TestSafetySeverity:
    def test_has_exactly_four_members(self) -> None:
        assert {member.value for member in SafetySeverity} == {
            "low",
            "moderate",
            "high",
            "critical",
        }


class TestGenerationStatus:
    def test_has_exactly_two_members(self) -> None:
        assert {member.value for member in GenerationStatus} == {"completed", "failed"}


class TestPatientSex:
    def test_has_exactly_four_members(self) -> None:
        assert {member.value for member in PatientSex} == {
            "male",
            "female",
            "other",
            "unspecified",
        }


class TestPregnancyStatus:
    def test_has_exactly_four_members(self) -> None:
        assert {member.value for member in PregnancyStatus} == {
            "not_pregnant",
            "pregnant",
            "unknown",
            "not_applicable",
        }
