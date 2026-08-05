"""`ContraindicationService` — this task's own explicitly-named
APPLICATION service, covering three of this task's own eighteen DETECT
categories: duplicate therapy, contraindications, and black box
warnings.

- `detect_duplicate_therapy` — pure, no port needed: flags when the
  *same* normalized `drug_name` (falling back to `generic_name` when
  `drug_name` differs but the active ingredient is the same is out of
  scope for this deterministic, table-free check — see this method's
  own docstring) appears more than once across `current_medications` +
  `new_prescription`. This is a genuinely different question from
  `domain/value_objects.py`'s own `DuplicateMedicationError` (which only
  ever inspects `current_medications` and only flags an *identical*
  entry reported twice): a new prescription duplicating a drug the
  patient is already on — even at a different dose — is exactly the
  clinical "duplicate therapy" concern this method exists to catch.
- `detect_contraindications`/`detect_black_box_warnings` — delegate
  per-medication to `MedicationSafetyPort.check_contraindication`/
  `.check_black_box_warning`.
"""

from app.modules.drug_interaction_ai.application.ports import MedicationSafetyPort
from app.modules.drug_interaction_ai.domain.enums import SafetyIssueCategory, SafetySeverity
from app.modules.drug_interaction_ai.domain.value_objects import MedicationEntry, SafetyIssue

_DUPLICATE_THERAPY = SafetyIssueCategory.DUPLICATE_THERAPY


class ContraindicationService:
    def __init__(self, *, port: MedicationSafetyPort) -> None:
        self._port = port

    def detect_duplicate_therapy(
        self, medications: tuple[MedicationEntry, ...]
    ) -> tuple[SafetyIssue, ...]:
        seen: set[str] = set()
        issues: list[SafetyIssue] = []
        for medication in medications:
            key = medication.drug_name.strip().lower()
            if key in seen:
                issues.append(
                    SafetyIssue(
                        category=_DUPLICATE_THERAPY,
                        description=f"{medication.drug_name} is reported more than once",
                        severity=SafetySeverity.MODERATE,
                        involved_medications=(medication.drug_name,),
                    )
                )
            seen.add(key)
        return tuple(issues)

    def detect_contraindications(self, medications: tuple[MedicationEntry, ...]) -> tuple[str, ...]:
        contraindications: list[str] = []
        for medication in medications:
            contraindication = self._port.check_contraindication(medication)
            if contraindication is not None:
                contraindications.append(contraindication)
        return tuple(contraindications)

    def detect_black_box_warnings(
        self, medications: tuple[MedicationEntry, ...]
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        for medication in medications:
            warning = self._port.check_black_box_warning(medication)
            if warning is not None:
                warnings.append(warning)
        return tuple(warnings)
