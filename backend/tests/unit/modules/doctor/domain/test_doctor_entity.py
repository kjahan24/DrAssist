"""Unit tests for the `Doctor` aggregate's invariants."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.doctor.domain.entities import Doctor
from app.modules.doctor.domain.enums import DoctorStatus
from app.modules.doctor.domain.events import (
    DoctorActivated,
    DoctorDeactivated,
    DoctorOnboarded,
    DoctorSuspended,
)
from app.modules.doctor.domain.exceptions import EmployeeIdRequiredError


def _make_doctor(**overrides: object) -> Doctor:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "user_id": uuid4(),
        "employee_id": "EMP-001",
        "joining_date": date(2026, 1, 1),
    }
    defaults.update(overrides)
    return Doctor.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_doctor_onboarded_event(self) -> None:
        organization_id = uuid4()
        user_id = uuid4()
        doctor = _make_doctor(organization_id=organization_id, user_id=user_id)

        assert doctor.organization_id == organization_id
        assert doctor.user_id == user_id
        assert doctor.status is DoctorStatus.ACTIVE
        events = doctor.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorOnboarded)
        assert events[0].employee_id == "EMP-001"

    def test_blank_employee_id_is_rejected(self) -> None:
        with pytest.raises(EmployeeIdRequiredError):
            _make_doctor(employee_id="   ")

    def test_employee_id_is_stripped(self) -> None:
        doctor = _make_doctor(employee_id="  EMP-002  ")
        assert doctor.employee_id == "EMP-002"


class TestBelongsToOneOrganization:
    def test_organization_id_is_fixed_at_creation(self) -> None:
        organization_id = uuid4()
        doctor = _make_doctor(organization_id=organization_id)
        assert doctor.organization_id == organization_id


class TestStatusTransitions:
    def test_deactivate_then_activate_round_trips(self) -> None:
        doctor = _make_doctor()
        doctor.pull_events()

        doctor.deactivate()
        assert doctor.status is DoctorStatus.INACTIVE
        events = doctor.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorDeactivated)

        doctor.activate()
        assert doctor.status is DoctorStatus.ACTIVE
        events = doctor.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorActivated)

    def test_suspend_records_event(self) -> None:
        doctor = _make_doctor()
        doctor.pull_events()

        doctor.suspend()
        assert doctor.status is DoctorStatus.SUSPENDED
        events = doctor.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorSuspended)

    def test_activating_an_already_active_doctor_is_idempotent(self) -> None:
        doctor = _make_doctor()
        doctor.pull_events()
        doctor.activate()
        assert doctor.pull_events() == []

    def test_suspending_an_already_suspended_doctor_is_idempotent(self) -> None:
        doctor = _make_doctor()
        doctor.suspend()
        doctor.pull_events()
        doctor.suspend()
        assert doctor.pull_events() == []
