"""Vital Signs module aggregate root: `VisitVitalSigns`.

A single aggregate for this foundation task. `VisitVitalSigns` is not
"owned by" the Visit module — like `PatientVisit` referencing `Patient`/
`Doctor`, it references `Visit` (`visit_id`) and, optionally, `Doctor`
(`recorded_by`) as peers, each by ID only (never an object reference),
validated by the application layer via those modules' public
`VisitQueryPort`/`DoctorQueryPort` (see
`application/use_cases/record_vital_signs.py`), never by importing across
`domain/` packages — see
`docs/backend-architecture/03_module_architecture.md`. All mutation goes
through named methods that enforce the aggregate's invariants and record
domain events; nothing here performs I/O.

`height_cm`, `weight_kg`, and `blood_glucose` deliberately carry no
numeric-range validation, unlike every other measurement here — the
approved business rules constrain `pain_score`, `spo2`, `temperature_c`,
`pulse_bpm`, and `respiratory_rate` explicitly, but say nothing about
these three, so none is invented. A future module task can add one if a
rule is specified.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from app.modules.vital_signs.domain.events import VisitVitalSignsRecorded, VisitVitalSignsUpdated
from app.modules.vital_signs.domain.exceptions import (
    InvalidPainScoreError,
    InvalidPulseError,
    InvalidRespiratoryRateError,
    InvalidSpo2Error,
    InvalidTemperatureError,
)
from app.modules.vital_signs.domain.value_objects import BloodPressure
from app.shared.domain.entity import AggregateRoot

# Extreme survivable range for a core body temperature reading — not a
# "normal" clinical range (which would wrongly reject genuine fevers or
# hypothermia), just the outer bound past which a reading is almost
# certainly a data-entry or device error rather than a real measurement.
_MIN_TEMPERATURE_C = Decimal("25.0")
_MAX_TEMPERATURE_C = Decimal("45.0")

_BMI_QUANTIZE = Decimal("0.1")


@dataclass(kw_only=True, eq=False)
class VisitVitalSigns(AggregateRoot):
    organization_id: UUID
    visit_id: UUID
    temperature_c: Decimal
    pulse_bpm: int
    respiratory_rate: int
    blood_pressure: BloodPressure
    spo2: int
    recorded_at: datetime
    recorded_by: UUID | None = None
    height_cm: Decimal | None = None
    weight_kg: Decimal | None = None
    bmi: Decimal | None = None
    blood_glucose: Decimal | None = None
    pain_score: int | None = None

    def __post_init__(self) -> None:
        _validate_temperature(self.temperature_c)
        _validate_pulse(self.pulse_bpm)
        _validate_respiratory_rate(self.respiratory_rate)
        _validate_spo2(self.spo2)
        _validate_pain_score(self.pain_score)
        self.bmi = calculate_bmi(height_cm=self.height_cm, weight_kg=self.weight_kg)

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        visit_id: UUID,
        temperature_c: Decimal,
        pulse_bpm: int,
        respiratory_rate: int,
        blood_pressure: BloodPressure,
        spo2: int,
        recorded_at: datetime,
        recorded_by: UUID | None = None,
        height_cm: Decimal | None = None,
        weight_kg: Decimal | None = None,
        blood_glucose: Decimal | None = None,
        pain_score: int | None = None,
    ) -> "VisitVitalSigns":
        """`bmi` is deliberately not a parameter here — it is always
        derived from `height_cm`/`weight_kg` in `__post_init__`, never
        supplied directly, so a stored `bmi` can never disagree with the
        measurements it was computed from."""
        vital_signs = cls(
            organization_id=organization_id,
            visit_id=visit_id,
            temperature_c=temperature_c,
            pulse_bpm=pulse_bpm,
            respiratory_rate=respiratory_rate,
            blood_pressure=blood_pressure,
            spo2=spo2,
            recorded_at=recorded_at,
            recorded_by=recorded_by,
            height_cm=height_cm,
            weight_kg=weight_kg,
            blood_glucose=blood_glucose,
            pain_score=pain_score,
        )
        vital_signs.record_event(
            VisitVitalSignsRecorded(
                vital_signs_id=vital_signs.id,
                organization_id=organization_id,
                visit_id=visit_id,
            )
        )
        return vital_signs

    def update_details(
        self,
        *,
        temperature_c: Decimal | None = None,
        pulse_bpm: int | None = None,
        respiratory_rate: int | None = None,
        blood_pressure: BloodPressure | None = None,
        spo2: int | None = None,
        recorded_at: datetime | None = None,
        recorded_by: UUID | None = None,
        height_cm: Decimal | None = None,
        weight_kg: Decimal | None = None,
        blood_glucose: Decimal | None = None,
        pain_score: int | None = None,
    ) -> None:
        if temperature_c is not None:
            _validate_temperature(temperature_c)
            self.temperature_c = temperature_c
        if pulse_bpm is not None:
            _validate_pulse(pulse_bpm)
            self.pulse_bpm = pulse_bpm
        if respiratory_rate is not None:
            _validate_respiratory_rate(respiratory_rate)
            self.respiratory_rate = respiratory_rate
        if blood_pressure is not None:
            self.blood_pressure = blood_pressure
        if spo2 is not None:
            _validate_spo2(spo2)
            self.spo2 = spo2
        if recorded_at is not None:
            self.recorded_at = recorded_at
        if recorded_by is not None:
            self.recorded_by = recorded_by
        if height_cm is not None:
            self.height_cm = height_cm
        if weight_kg is not None:
            self.weight_kg = weight_kg
        if blood_glucose is not None:
            self.blood_glucose = blood_glucose
        if pain_score is not None:
            _validate_pain_score(pain_score)
            self.pain_score = pain_score

        self.bmi = calculate_bmi(height_cm=self.height_cm, weight_kg=self.weight_kg)
        self.touch()
        self.record_event(VisitVitalSignsUpdated(vital_signs_id=self.id, visit_id=self.visit_id))


def calculate_bmi(*, height_cm: Decimal | None, weight_kg: Decimal | None) -> Decimal | None:
    """BMI = weight_kg / height_m^2, rounded to one decimal place — the
    precision clinical vital-signs charts conventionally display. `None`
    unless both measurements are available, matching "BMI must be
    calculated automatically when height and weight are available" (and,
    implicitly, not otherwise)."""
    if height_cm is None or weight_kg is None:
        return None
    height_m = height_cm / Decimal("100")
    bmi = weight_kg / (height_m * height_m)
    return bmi.quantize(_BMI_QUANTIZE, rounding=ROUND_HALF_UP)


def _validate_temperature(value: Decimal) -> None:
    if value < _MIN_TEMPERATURE_C or value > _MAX_TEMPERATURE_C:
        raise InvalidTemperatureError(value)


def _validate_pulse(value: int) -> None:
    if value <= 0:
        raise InvalidPulseError(value)


def _validate_respiratory_rate(value: int) -> None:
    if value <= 0:
        raise InvalidRespiratoryRateError(value)


def _validate_spo2(value: int) -> None:
    if value < 0 or value > 100:
        raise InvalidSpo2Error(value)


def _validate_pain_score(value: int | None) -> None:
    if value is not None and (value < 0 or value > 10):
        raise InvalidPainScoreError(value)
