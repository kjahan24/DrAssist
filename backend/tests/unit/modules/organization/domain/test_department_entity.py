"""Unit tests for the `Department` aggregate's invariants."""

from uuid import uuid4

import pytest

from app.modules.organization.domain.entities import Department
from app.modules.organization.domain.enums import DepartmentStatus
from app.modules.organization.domain.events import DepartmentCreated, DepartmentStatusChanged
from app.modules.organization.domain.exceptions import DepartmentNameRequiredError


class TestCreate:
    def test_create_records_department_created_event(self) -> None:
        organization_id = uuid4()
        department = Department.create(organization_id=organization_id, name="Cardiology")

        assert department.organization_id == organization_id
        assert department.status is DepartmentStatus.ACTIVE
        events = department.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DepartmentCreated)
        assert events[0].name == "Cardiology"

    def test_blank_name_is_rejected(self) -> None:
        with pytest.raises(DepartmentNameRequiredError):
            Department.create(organization_id=uuid4(), name="   ")

    def test_name_is_stripped(self) -> None:
        department = Department.create(organization_id=uuid4(), name="  Cardiology  ")
        assert department.name == "Cardiology"


class TestBelongsToOneOrganization:
    def test_organization_id_is_fixed_at_creation(self) -> None:
        organization_id = uuid4()
        department = Department.create(organization_id=organization_id, name="Radiology")
        assert department.organization_id == organization_id


class TestStatusTransitions:
    def test_deactivate_then_activate_round_trips(self) -> None:
        department = Department.create(organization_id=uuid4(), name="Radiology")
        department.pull_events()

        department.deactivate()
        assert department.status is DepartmentStatus.INACTIVE
        events = department.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DepartmentStatusChanged)
        assert events[0].status == "inactive"

        department.activate()
        assert department.status is DepartmentStatus.ACTIVE

    def test_activating_an_already_active_department_is_idempotent(self) -> None:
        department = Department.create(organization_id=uuid4(), name="Radiology")
        department.pull_events()
        department.activate()
        assert department.pull_events() == []


class TestUpdateDetails:
    def test_update_details_changes_name_and_description(self) -> None:
        department = Department.create(organization_id=uuid4(), name="Radiology")
        department.pull_events()

        department.update_details(name="Diagnostic Radiology", description="Imaging services")

        assert department.name == "Diagnostic Radiology"
        assert department.description == "Imaging services"
        assert len(department.pull_events()) == 1

    def test_update_details_rejects_blank_name(self) -> None:
        department = Department.create(organization_id=uuid4(), name="Radiology")
        with pytest.raises(DepartmentNameRequiredError):
            department.update_details(name="  ")
