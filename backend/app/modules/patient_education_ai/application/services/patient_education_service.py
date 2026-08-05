"""`PatientEducationService` — this task's own explicitly-named
APPLICATION service, the thin orchestration layer over
`PatientEducationPort` that turns the caller-supplied `diagnoses` list
into deterministic, curated patient-facing content:

- `build_diagnosis_explanation` — this task's own "Diagnosis
  Explanation" OUTPUT field: combines each recognized diagnosis's own
  curated explanation into one narrative, skipping any diagnosis the
  port has no reference data for.
- `collect_warning_signs`/`collect_emergency_symptoms` — this task's
  own "Warning Signs"/"Emergency Instructions" OUTPUT fields: the
  deduplicated union of every recognized diagnosis's own curated
  warning signs/emergency symptoms.
"""

from app.modules.patient_education_ai.application.ports import PatientEducationPort
from app.modules.patient_education_ai.application.services._dedupe import (
    dedupe_preserving_order,
)


class PatientEducationService:
    def __init__(self, *, education_port: PatientEducationPort) -> None:
        self._education_port = education_port

    def build_diagnosis_explanation(self, diagnoses: tuple[str, ...]) -> str:
        explanations = [
            explanation
            for diagnosis in diagnoses
            if (explanation := self._education_port.explain_diagnosis(diagnosis)) is not None
        ]
        return " ".join(explanations)

    def collect_warning_signs(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]:
        signs: list[str] = []
        for diagnosis in diagnoses:
            signs.extend(self._education_port.identify_warning_signs(diagnosis))
        return dedupe_preserving_order(tuple(signs))

    def collect_emergency_symptoms(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]:
        symptoms: list[str] = []
        for diagnosis in diagnoses:
            symptoms.extend(self._education_port.identify_emergency_symptoms(diagnosis))
        return dedupe_preserving_order(tuple(symptoms))
