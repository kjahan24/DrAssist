"""Domain exceptions for the Vital Signs module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`. A
missing referenced `Visit`/`Doctor` raises the *owning* module's own
`PatientVisitNotFoundError`/`DoctorNotFoundError` directly (see
`application/use_cases/record_vital_signs.py`), not a Vital-Signs-specific
wrapper — the same cross-module reuse already established by
`app.modules.visit.application.use_cases.schedule_visit.ScheduleVisit` and
`app.modules.patient.application.use_cases.record_patient_allergy.RecordPatientAllergy`.
"""

from decimal import Decimal
from uuid import UUID

from app.shared.domain.exceptions import DomainError


class DuplicateVitalSignsForVisitError(DomainError):
    def __init__(self, visit_id: UUID) -> None:
        super().__init__(f"visit {visit_id} already has a vital signs record")
        self.visit_id = visit_id


class InvalidBloodPressureError(DomainError):
    def __init__(self, systolic: int, diastolic: int) -> None:
        super().__init__(
            f"systolic_bp ({systolic}) must be greater than diastolic_bp ({diastolic})"
        )
        self.systolic = systolic
        self.diastolic = diastolic


class InvalidTemperatureError(DomainError):
    def __init__(self, value: Decimal) -> None:
        super().__init__(f"temperature_c {value} is outside the medically reasonable range")
        self.value = value


class InvalidPulseError(DomainError):
    def __init__(self, value: int) -> None:
        super().__init__(f"pulse_bpm must be positive, got {value}")
        self.value = value


class InvalidRespiratoryRateError(DomainError):
    def __init__(self, value: int) -> None:
        super().__init__(f"respiratory_rate must be positive, got {value}")
        self.value = value


class InvalidSpo2Error(DomainError):
    def __init__(self, value: int) -> None:
        super().__init__(f"spo2 must be between 0 and 100, got {value}")
        self.value = value


class InvalidPainScoreError(DomainError):
    def __init__(self, value: int) -> None:
        super().__init__(f"pain_score must be between 0 and 10, got {value}")
        self.value = value
