"""`MedicationSafetyService` — this task's own explicitly-named
APPLICATION service, covering twelve of this task's own eighteen DETECT
categories: drug-allergy interactions, drug-disease interactions, QT
prolongation/serotonin syndrome/bleeding/nephrotoxicity/hepatotoxicity
risk, medication reconciliation issues, high-risk elderly medication,
pediatric dose safety, pregnancy safety, and lactation safety.

- `detect_patient_context_risks` — delegates per-medication to
  `MedicationSafetyPort.check_patient_context_risks`, passing this
  task's own SUPPORTED INPUT patient-context fields through unchanged
  (covers drug-allergy, drug-disease, pregnancy safety, lactation
  safety, high-risk-elderly, and pediatric-dose-safety — six
  categories).
- `detect_pharmacologic_risk_flags` — delegates per-medication to
  `MedicationSafetyPort.classify_pharmacologic_risk_flags`, wrapping
  each returned category into a `SafetyIssue` (covers QT prolongation,
  serotonin syndrome, bleeding, nephrotoxicity, and hepatotoxicity risk —
  five categories).
- `detect_reconciliation_issues` — pure, no port needed: flags when the
  *same* medication (by normalized `drug_name`) appears in
  `current_medications` with *different* dose/frequency/route across
  entries — a genuine reconciliation problem (conflicting records of
  what the patient is actually taking), distinct from
  `domain/value_objects.py`'s own `DuplicateMedicationError` (which
  catches the *identical* entry reported twice, a pure data-entry
  error). Covers "Medication Reconciliation Issues", the twelfth and
  final category this service owns.
"""

from app.modules.drug_interaction_ai.application.ports import MedicationSafetyPort
from app.modules.drug_interaction_ai.domain.enums import (
    LactationStatus,
    PregnancyStatus,
    SafetyIssueCategory,
    SafetySeverity,
)
from app.modules.drug_interaction_ai.domain.value_objects import MedicationEntry, SafetyIssue

_RECONCILIATION = SafetyIssueCategory.MEDICATION_RECONCILIATION_ISSUE


class MedicationSafetyService:
    def __init__(self, *, port: MedicationSafetyPort) -> None:
        self._port = port

    def detect_patient_context_risks(
        self,
        medications: tuple[MedicationEntry, ...],
        *,
        allergies: tuple[str, ...],
        medical_conditions: tuple[str, ...],
        pregnancy_status: PregnancyStatus | None,
        lactation_status: LactationStatus | None,
        patient_age: int | None,
    ) -> tuple[SafetyIssue, ...]:
        issues: list[SafetyIssue] = []
        for medication in medications:
            issues.extend(
                self._port.check_patient_context_risks(
                    medication,
                    allergies=allergies,
                    medical_conditions=medical_conditions,
                    pregnancy_status=pregnancy_status,
                    lactation_status=lactation_status,
                    patient_age=patient_age,
                )
            )
        return tuple(issues)

    def detect_pharmacologic_risk_flags(
        self, medications: tuple[MedicationEntry, ...]
    ) -> tuple[SafetyIssue, ...]:
        issues: list[SafetyIssue] = []
        for medication in medications:
            for category in self._port.classify_pharmacologic_risk_flags(medication):
                risk_name = category.value.replace("_", " ")
                issues.append(
                    SafetyIssue(
                        category=category,
                        description=f"{medication.drug_name} carries a {risk_name}",
                        severity=SafetySeverity.MODERATE,
                        involved_medications=(medication.drug_name,),
                    )
                )
        return tuple(issues)

    def detect_reconciliation_issues(
        self, medications: tuple[MedicationEntry, ...]
    ) -> tuple[SafetyIssue, ...]:
        seen: dict[str, MedicationEntry] = {}
        issues: list[SafetyIssue] = []
        flagged: set[str] = set()
        for medication in medications:
            key = medication.drug_name.strip().lower()
            prior = seen.get(key)
            if (
                prior is not None
                and key not in flagged
                and (prior.dose, prior.frequency, prior.route)
                != (medication.dose, medication.frequency, medication.route)
            ):
                issues.append(
                    SafetyIssue(
                        category=_RECONCILIATION,
                        description=(
                            f"{medication.drug_name} appears with conflicting dose, "
                            "frequency, or route across the supplied medication list"
                        ),
                        severity=SafetySeverity.MODERATE,
                        involved_medications=(medication.drug_name,),
                    )
                )
                flagged.add(key)
            seen[key] = medication
        return tuple(issues)
