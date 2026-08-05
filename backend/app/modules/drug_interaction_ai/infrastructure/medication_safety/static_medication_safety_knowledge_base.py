"""`StaticMedicationSafetyKnowledgeBase` — the one concrete
`MedicationSafetyPort` implementation this task ships: small, curated
reference tables covering drug-allergy cross-reactivity, drug-disease
contraindication, pregnancy/lactation risk, high-risk-elderly/pediatric-
unsafe medications, pharmacologic risk flags, contraindications, and
black box warnings. A real production system might instead consult a
licensed, comprehensive drug-safety database here; this module's own
small, table-driven implementation is the pragmatic in-repo substitute,
the same "each module defines its own local, necessarily-incomplete
copy" precedent every prior AI module's own knowledge-base adapter
establishes for itself.
"""

from app.modules.drug_interaction_ai.application.ports import MedicationSafetyPort
from app.modules.drug_interaction_ai.domain.enums import (
    LactationStatus,
    PregnancyStatus,
    SafetyIssueCategory,
    SafetySeverity,
)
from app.modules.drug_interaction_ai.domain.value_objects import MedicationEntry, SafetyIssue

_ALLERGY_CROSS_REACTIVITY: dict[str, tuple[str, ...]] = {
    "amoxicillin": ("penicillin", "amoxicillin", "beta-lactam"),
    "ampicillin": ("penicillin", "ampicillin", "beta-lactam"),
    "penicillin": ("penicillin", "beta-lactam"),
    "cephalexin": ("cephalosporin", "penicillin"),
    "sulfamethoxazole": ("sulfa", "sulfonamide"),
    "codeine": ("codeine", "opioid"),
}

_DISEASE_CONTRAINDICATIONS: dict[str, tuple[str, ...]] = {
    "ibuprofen": ("peptic ulcer", "renal failure", "gi bleed"),
    "aspirin": ("peptic ulcer", "gi bleed"),
    "metformin": ("renal failure", "ckd"),
    "propranolol": ("asthma", "copd"),
}

_PREGNANCY_RISK_DRUGS = frozenset(
    {"warfarin", "lisinopril", "isotretinoin", "methotrexate", "valproate"}
)

_LACTATION_RISK_DRUGS = frozenset({"methotrexate", "lithium", "amiodarone"})

_ELDERLY_HIGH_RISK_DRUGS = frozenset({"diphenhydramine", "diazepam", "amitriptyline"})

_PEDIATRIC_UNSAFE_DRUGS = frozenset({"aspirin", "tetracycline", "codeine"})

_PEDIATRIC_AGE_THRESHOLD = 18
_ELDERLY_AGE_THRESHOLD = 65

_PHARMACOLOGIC_RISK_FLAGS: dict[str, tuple[SafetyIssueCategory, ...]] = {
    "ondansetron": (SafetyIssueCategory.QT_PROLONGATION_RISK,),
    "citalopram": (SafetyIssueCategory.QT_PROLONGATION_RISK,),
    "haloperidol": (SafetyIssueCategory.QT_PROLONGATION_RISK,),
    "sertraline": (SafetyIssueCategory.SEROTONIN_SYNDROME_RISK,),
    "tramadol": (SafetyIssueCategory.SEROTONIN_SYNDROME_RISK,),
    "warfarin": (SafetyIssueCategory.BLEEDING_RISK,),
    "aspirin": (SafetyIssueCategory.BLEEDING_RISK,),
    "clopidogrel": (SafetyIssueCategory.BLEEDING_RISK,),
    "ibuprofen": (SafetyIssueCategory.NEPHROTOXICITY_RISK,),
    "gentamicin": (SafetyIssueCategory.NEPHROTOXICITY_RISK,),
    "vancomycin": (SafetyIssueCategory.NEPHROTOXICITY_RISK,),
    "acetaminophen": (SafetyIssueCategory.HEPATOTOXICITY_RISK,),
    "methotrexate": (SafetyIssueCategory.HEPATOTOXICITY_RISK,),
    "amiodarone": (
        SafetyIssueCategory.HEPATOTOXICITY_RISK,
        SafetyIssueCategory.QT_PROLONGATION_RISK,
    ),
}

_CONTRAINDICATIONS: dict[str, str] = {
    "sildenafil": "Contraindicated with concurrent nitrate use due to risk of severe hypotension.",
    "metformin": "Contraindicated in severe renal impairment (eGFR < 30 mL/min/1.73m2).",
    "isotretinoin": "Contraindicated in pregnancy due to severe teratogenic risk.",
}

_BLACK_BOX_WARNINGS: dict[str, str] = {
    "warfarin": "Black Box Warning: can cause major or fatal bleeding.",
    "metoclopramide": "Black Box Warning: risk of tardive dyskinesia with prolonged use.",
    "ciprofloxacin": (
        "Black Box Warning: risk of tendinitis, tendon rupture, and peripheral neuropathy."
    ),
    "citalopram": "Black Box Warning: dose-dependent QT interval prolongation risk.",
}


class StaticMedicationSafetyKnowledgeBase(MedicationSafetyPort):
    def check_patient_context_risks(
        self,
        medication: MedicationEntry,
        *,
        allergies: tuple[str, ...],
        medical_conditions: tuple[str, ...],
        pregnancy_status: PregnancyStatus | None,
        lactation_status: LactationStatus | None,
        patient_age: int | None,
    ) -> tuple[SafetyIssue, ...]:
        issues: list[SafetyIssue] = []
        drug_key = medication.drug_name.strip().lower()

        allergy_issue = self._check_allergy(medication, drug_key, allergies)
        if allergy_issue is not None:
            issues.append(allergy_issue)

        disease_issue = self._check_disease(medication, drug_key, medical_conditions)
        if disease_issue is not None:
            issues.append(disease_issue)

        if pregnancy_status is PregnancyStatus.PREGNANT and drug_key in _PREGNANCY_RISK_DRUGS:
            issues.append(
                SafetyIssue(
                    category=SafetyIssueCategory.PREGNANCY_SAFETY,
                    description=f"{medication.drug_name} carries a known pregnancy safety risk.",
                    severity=SafetySeverity.MAJOR,
                    involved_medications=(medication.drug_name,),
                )
            )

        if lactation_status is LactationStatus.LACTATING and drug_key in _LACTATION_RISK_DRUGS:
            issues.append(
                SafetyIssue(
                    category=SafetyIssueCategory.LACTATION_SAFETY,
                    description=f"{medication.drug_name} carries a known lactation safety risk.",
                    severity=SafetySeverity.MODERATE,
                    involved_medications=(medication.drug_name,),
                )
            )

        if (
            patient_age is not None
            and patient_age >= _ELDERLY_AGE_THRESHOLD
            and drug_key in _ELDERLY_HIGH_RISK_DRUGS
        ):
            issues.append(
                SafetyIssue(
                    category=SafetyIssueCategory.HIGH_RISK_ELDERLY_MEDICATION,
                    description=(
                        f"{medication.drug_name} is a high-risk medication in elderly patients."
                    ),
                    severity=SafetySeverity.MODERATE,
                    involved_medications=(medication.drug_name,),
                )
            )

        if (
            patient_age is not None
            and patient_age < _PEDIATRIC_AGE_THRESHOLD
            and drug_key in _PEDIATRIC_UNSAFE_DRUGS
        ):
            issues.append(
                SafetyIssue(
                    category=SafetyIssueCategory.PEDIATRIC_DOSE_SAFETY,
                    description=(
                        f"{medication.drug_name} requires special caution in pediatric patients."
                    ),
                    severity=SafetySeverity.MODERATE,
                    involved_medications=(medication.drug_name,),
                )
            )

        return tuple(issues)

    def _check_allergy(
        self, medication: MedicationEntry, drug_key: str, allergies: tuple[str, ...]
    ) -> SafetyIssue | None:
        keywords = _ALLERGY_CROSS_REACTIVITY.get(drug_key, ())
        for allergy in allergies:
            allergy_lower = allergy.strip().lower()
            if any(keyword in allergy_lower for keyword in keywords):
                return SafetyIssue(
                    category=SafetyIssueCategory.DRUG_ALLERGY_INTERACTION,
                    description=(
                        f"{medication.drug_name} may cross-react with reported {allergy} allergy."
                    ),
                    severity=SafetySeverity.MAJOR,
                    involved_medications=(medication.drug_name,),
                )
        return None

    def _check_disease(
        self, medication: MedicationEntry, drug_key: str, medical_conditions: tuple[str, ...]
    ) -> SafetyIssue | None:
        keywords = _DISEASE_CONTRAINDICATIONS.get(drug_key, ())
        for condition in medical_conditions:
            condition_lower = condition.strip().lower()
            if any(keyword in condition_lower for keyword in keywords):
                return SafetyIssue(
                    category=SafetyIssueCategory.DRUG_DISEASE_INTERACTION,
                    description=f"{medication.drug_name} may be unsafe given {condition}.",
                    severity=SafetySeverity.MODERATE,
                    involved_medications=(medication.drug_name,),
                )
        return None

    def classify_pharmacologic_risk_flags(
        self, medication: MedicationEntry
    ) -> tuple[SafetyIssueCategory, ...]:
        return _PHARMACOLOGIC_RISK_FLAGS.get(medication.drug_name.strip().lower(), ())

    def check_contraindication(self, medication: MedicationEntry) -> str | None:
        return _CONTRAINDICATIONS.get(medication.drug_name.strip().lower())

    def check_black_box_warning(self, medication: MedicationEntry) -> str | None:
        return _BLACK_BOX_WARNINGS.get(medication.drug_name.strip().lower())
