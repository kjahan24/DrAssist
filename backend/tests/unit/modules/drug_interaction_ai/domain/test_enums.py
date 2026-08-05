"""Unit tests for the AI Drug Interaction & Medication Safety module's
domain enums."""

from app.modules.drug_interaction_ai.domain.enums import (
    DrugInteractionOutputFormat,
    DrugInteractionSetting,
    EvidenceLevel,
    LactationStatus,
    PregnancyStatus,
    SafetyAnalysisStatus,
    SafetyIssueCategory,
    SafetySeverity,
)


class TestDrugInteractionSetting:
    def test_has_the_seven_settings_this_tasks_prompts_section_names_in_order(self) -> None:
        assert list(DrugInteractionSetting) == [
            DrugInteractionSetting.OUTPATIENT,
            DrugInteractionSetting.INPATIENT,
            DrugInteractionSetting.EMERGENCY,
            DrugInteractionSetting.ICU,
            DrugInteractionSetting.PEDIATRIC,
            DrugInteractionSetting.GERIATRIC,
            DrugInteractionSetting.PREGNANCY,
        ]

    def test_includes_icu_and_pregnancy(self) -> None:
        values = {member.value for member in DrugInteractionSetting}
        assert "icu" in values
        assert "pregnancy" in values


class TestDrugInteractionOutputFormat:
    def test_has_json_markdown_and_text(self) -> None:
        assert {member.value for member in DrugInteractionOutputFormat} == {
            "json",
            "markdown",
            "text",
        }


class TestSafetyIssueCategory:
    def test_has_eighteen_categories(self) -> None:
        assert len(list(SafetyIssueCategory)) == 18

    def test_includes_every_named_detect_category(self) -> None:
        values = {member.value for member in SafetyIssueCategory}
        assert values == {
            "drug_drug_interaction",
            "drug_allergy_interaction",
            "drug_disease_interaction",
            "duplicate_therapy",
            "contraindication",
            "black_box_warning",
            "qt_prolongation_risk",
            "serotonin_syndrome_risk",
            "bleeding_risk",
            "nephrotoxicity_risk",
            "hepatotoxicity_risk",
            "medication_reconciliation_issue",
            "high_risk_elderly_medication",
            "pediatric_dose_safety",
            "pregnancy_safety",
            "lactation_safety",
            "renal_dose_adjustment",
            "hepatic_dose_adjustment",
        }


class TestSafetySeverity:
    def test_has_the_four_severities_in_ascending_order(self) -> None:
        assert list(SafetySeverity) == [
            SafetySeverity.MINOR,
            SafetySeverity.MODERATE,
            SafetySeverity.MAJOR,
            SafetySeverity.CONTRAINDICATED,
        ]


class TestEvidenceLevel:
    def test_has_the_four_evidence_levels_in_descending_order(self) -> None:
        assert list(EvidenceLevel) == [
            EvidenceLevel.ESTABLISHED,
            EvidenceLevel.PROBABLE,
            EvidenceLevel.SUSPECTED,
            EvidenceLevel.THEORETICAL,
        ]


class TestSafetyAnalysisStatus:
    def test_has_completed_and_failed(self) -> None:
        assert {member.value for member in SafetyAnalysisStatus} == {"completed", "failed"}


class TestPregnancyStatus:
    def test_has_four_members(self) -> None:
        assert {member.value for member in PregnancyStatus} == {
            "not_pregnant",
            "pregnant",
            "unknown",
            "not_applicable",
        }


class TestLactationStatus:
    def test_has_four_members(self) -> None:
        assert {member.value for member in LactationStatus} == {
            "lactating",
            "not_lactating",
            "unknown",
            "not_applicable",
        }
