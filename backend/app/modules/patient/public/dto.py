"""Public DTOs — the only data shapes another module may depend on.

Re-exported from the application layer's `dto.py`, not redefined, so
there is exactly one definition of each shape.

`PatientAllergySummaryDTO`/`PatientMedicalConditionSummaryDTO` were added
alongside `PatientQueryPort.list_allergies_for_patient`/
`list_medical_conditions_for_patient` — see that file's own docstring.
"""

from app.modules.patient.application.dto import (
    PatientAllergySummaryDTO,
    PatientMedicalConditionSummaryDTO,
    PatientSummaryDTO,
)

__all__ = ["PatientAllergySummaryDTO", "PatientMedicalConditionSummaryDTO", "PatientSummaryDTO"]
