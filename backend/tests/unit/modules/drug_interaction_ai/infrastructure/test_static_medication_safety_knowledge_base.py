"""Unit tests for `StaticMedicationSafetyKnowledgeBase`."""

from app.modules.drug_interaction_ai.domain.enums import (
    LactationStatus,
    PregnancyStatus,
    SafetyIssueCategory,
)
from app.modules.drug_interaction_ai.domain.value_objects import MedicationEntry, SafetyIssue
from app.modules.drug_interaction_ai.infrastructure.medication_safety.static_medication_safety_knowledge_base import (  # noqa: E501
    StaticMedicationSafetyKnowledgeBase,
)


def _medication(**overrides: object) -> MedicationEntry:
    defaults: dict[str, object] = {"drug_name": "Warfarin"}
    defaults.update(overrides)
    return MedicationEntry(**defaults)  # type: ignore[arg-type]


def _check_context_risks(
    kb: StaticMedicationSafetyKnowledgeBase,
    medication: MedicationEntry,
    *,
    allergies: tuple[str, ...] = (),
    medical_conditions: tuple[str, ...] = (),
    pregnancy_status: PregnancyStatus | None = None,
    lactation_status: LactationStatus | None = None,
    patient_age: int | None = None,
) -> tuple[SafetyIssue, ...]:
    return kb.check_patient_context_risks(
        medication,
        allergies=allergies,
        medical_conditions=medical_conditions,
        pregnancy_status=pregnancy_status,
        lactation_status=lactation_status,
        patient_age=patient_age,
    )


class TestCheckPatientContextRisksAllergy:
    def test_flags_a_cross_reactive_allergy(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()

        issues = _check_context_risks(
            kb, _medication(drug_name="Amoxicillin"), allergies=("Penicillin",)
        )

        categories = {i.category for i in issues}
        assert SafetyIssueCategory.DRUG_ALLERGY_INTERACTION in categories

    def test_no_flag_for_an_unrelated_allergy(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()

        issues = _check_context_risks(
            kb, _medication(drug_name="Amoxicillin"), allergies=("Latex",)
        )

        assert issues == ()

    def test_no_flag_when_the_drug_has_no_allergy_data(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()

        issues = _check_context_risks(
            kb, _medication(drug_name="Metformin"), allergies=("Penicillin",)
        )

        assert issues == ()


class TestCheckPatientContextRisksDisease:
    def test_flags_a_contraindicated_condition(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()

        issues = _check_context_risks(
            kb,
            _medication(drug_name="Ibuprofen"),
            medical_conditions=("Peptic ulcer disease",),
        )

        categories = {i.category for i in issues}
        assert SafetyIssueCategory.DRUG_DISEASE_INTERACTION in categories

    def test_no_flag_for_an_unrelated_condition(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()

        issues = _check_context_risks(
            kb, _medication(drug_name="Ibuprofen"), medical_conditions=("Migraine",)
        )

        assert issues == ()


class TestCheckPatientContextRisksPregnancy:
    def test_flags_a_pregnancy_risk_drug_when_pregnant(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()

        issues = _check_context_risks(
            kb, _medication(drug_name="Warfarin"), pregnancy_status=PregnancyStatus.PREGNANT
        )

        categories = {i.category for i in issues}
        assert SafetyIssueCategory.PREGNANCY_SAFETY in categories

    def test_no_flag_when_not_pregnant(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()

        issues = _check_context_risks(
            kb,
            _medication(drug_name="Warfarin"),
            pregnancy_status=PregnancyStatus.NOT_PREGNANT,
        )

        assert issues == ()

    def test_no_flag_for_a_drug_with_no_pregnancy_risk_data(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()

        issues = _check_context_risks(
            kb,
            _medication(drug_name="Acetaminophen"),
            pregnancy_status=PregnancyStatus.PREGNANT,
        )

        assert issues == ()


class TestCheckPatientContextRisksLactation:
    def test_flags_a_lactation_risk_drug_when_lactating(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()

        issues = _check_context_risks(
            kb,
            _medication(drug_name="Methotrexate"),
            lactation_status=LactationStatus.LACTATING,
        )

        categories = {i.category for i in issues}
        assert SafetyIssueCategory.LACTATION_SAFETY in categories

    def test_no_flag_when_not_lactating(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()

        issues = _check_context_risks(
            kb,
            _medication(drug_name="Methotrexate"),
            lactation_status=LactationStatus.NOT_LACTATING,
        )

        assert issues == ()


class TestCheckPatientContextRisksElderly:
    def test_flags_a_high_risk_elderly_medication(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()

        issues = _check_context_risks(kb, _medication(drug_name="Diphenhydramine"), patient_age=70)

        categories = {i.category for i in issues}
        assert SafetyIssueCategory.HIGH_RISK_ELDERLY_MEDICATION in categories

    def test_no_flag_below_the_elderly_age_threshold(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()

        issues = _check_context_risks(kb, _medication(drug_name="Diphenhydramine"), patient_age=40)

        assert issues == ()

    def test_boundary_age_is_flagged(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()

        issues = _check_context_risks(kb, _medication(drug_name="Diphenhydramine"), patient_age=65)

        categories = {i.category for i in issues}
        assert SafetyIssueCategory.HIGH_RISK_ELDERLY_MEDICATION in categories


class TestCheckPatientContextRisksPediatric:
    def test_flags_a_pediatric_unsafe_medication(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()

        issues = _check_context_risks(kb, _medication(drug_name="Aspirin"), patient_age=10)

        categories = {i.category for i in issues}
        assert SafetyIssueCategory.PEDIATRIC_DOSE_SAFETY in categories

    def test_no_flag_at_or_above_adulthood(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()

        issues = _check_context_risks(kb, _medication(drug_name="Aspirin"), patient_age=18)

        assert issues == ()

    def test_no_flag_when_age_is_not_given(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()

        issues = _check_context_risks(kb, _medication(drug_name="Aspirin"))

        assert issues == ()


class TestCheckPatientContextRisksCombined:
    def test_returns_no_issues_for_a_low_risk_medication(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()
        issues = _check_context_risks(kb, _medication(drug_name="Metformin"))
        assert issues == ()

    def test_can_return_multiple_issues_for_one_medication(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()

        issues = _check_context_risks(
            kb,
            _medication(drug_name="Warfarin"),
            pregnancy_status=PregnancyStatus.PREGNANT,
            patient_age=70,
        )

        categories = {i.category for i in issues}
        assert SafetyIssueCategory.PREGNANCY_SAFETY in categories


class TestClassifyPharmacologicRiskFlags:
    def test_returns_empty_for_an_unrecognized_drug(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()
        assert kb.classify_pharmacologic_risk_flags(_medication(drug_name="Metformin")) == ()

    def test_recognizes_qt_prolongation_risk(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()
        flags = kb.classify_pharmacologic_risk_flags(_medication(drug_name="Ondansetron"))
        assert SafetyIssueCategory.QT_PROLONGATION_RISK in flags

    def test_recognizes_serotonin_syndrome_risk(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()
        flags = kb.classify_pharmacologic_risk_flags(_medication(drug_name="Sertraline"))
        assert SafetyIssueCategory.SEROTONIN_SYNDROME_RISK in flags

    def test_recognizes_bleeding_risk(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()
        flags = kb.classify_pharmacologic_risk_flags(_medication(drug_name="Warfarin"))
        assert SafetyIssueCategory.BLEEDING_RISK in flags

    def test_recognizes_nephrotoxicity_risk(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()
        flags = kb.classify_pharmacologic_risk_flags(_medication(drug_name="Gentamicin"))
        assert SafetyIssueCategory.NEPHROTOXICITY_RISK in flags

    def test_recognizes_hepatotoxicity_risk(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()
        flags = kb.classify_pharmacologic_risk_flags(_medication(drug_name="Acetaminophen"))
        assert SafetyIssueCategory.HEPATOTOXICITY_RISK in flags

    def test_a_drug_can_carry_multiple_risk_flags(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()
        flags = kb.classify_pharmacologic_risk_flags(_medication(drug_name="Amiodarone"))
        assert SafetyIssueCategory.HEPATOTOXICITY_RISK in flags
        assert SafetyIssueCategory.QT_PROLONGATION_RISK in flags

    def test_is_case_insensitive(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()
        flags = kb.classify_pharmacologic_risk_flags(_medication(drug_name="WARFARIN"))
        assert SafetyIssueCategory.BLEEDING_RISK in flags


class TestCheckContraindication:
    def test_returns_none_for_an_unrecognized_drug(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()
        assert kb.check_contraindication(_medication(drug_name="Digoxin")) is None

    def test_returns_curated_text_for_a_recognized_drug(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()
        result = kb.check_contraindication(_medication(drug_name="Sildenafil"))
        assert result is not None
        assert "nitrate" in result.lower()


class TestCheckBlackBoxWarning:
    def test_returns_none_for_an_unrecognized_drug(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()
        assert kb.check_black_box_warning(_medication(drug_name="Metformin")) is None

    def test_returns_curated_text_for_a_recognized_drug(self) -> None:
        kb = StaticMedicationSafetyKnowledgeBase()
        result = kb.check_black_box_warning(_medication(drug_name="Warfarin"))
        assert result is not None
        assert "bleeding" in result.lower()
