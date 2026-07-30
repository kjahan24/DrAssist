"""Unit tests for `AppointmentQueryService` — backs the module's public
`AppointmentQueryPort` facade."""

from datetime import date, time
from uuid import uuid4

import pytest

from app.modules.appointment.application.services.appointment_query_service import (
    AppointmentQueryService,
)
from app.modules.appointment.domain.entities import Appointment
from app.modules.appointment.domain.enums import AppointmentType
from tests.unit.modules.appointment.application.fakes import FakeAppointmentRepository


def _make_appointment(**overrides: object) -> Appointment:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "doctor_id": uuid4(),
        "appointment_number": "APT-0001",
        "appointment_date": date(2026, 2, 1),
        "start_time": time(9, 0),
        "end_time": time(9, 30),
        "appointment_type": AppointmentType.CONSULTATION,
    }
    defaults.update(overrides)
    return Appointment.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def repo() -> FakeAppointmentRepository:
    return FakeAppointmentRepository()


@pytest.fixture
def service(repo: FakeAppointmentRepository) -> AppointmentQueryService:
    return AppointmentQueryService(appointment_repository=repo)


class TestAppointmentExists:
    async def test_true_for_a_known_appointment(
        self, service: AppointmentQueryService, repo: FakeAppointmentRepository
    ) -> None:
        appointment = _make_appointment()
        await repo.add(appointment)
        assert await service.appointment_exists(appointment.id) is True

    async def test_false_for_an_unknown_appointment(self, service: AppointmentQueryService) -> None:
        assert await service.appointment_exists(uuid4()) is False


class TestIsEditable:
    async def test_true_while_scheduled(
        self, service: AppointmentQueryService, repo: FakeAppointmentRepository
    ) -> None:
        appointment = _make_appointment()
        await repo.add(appointment)
        assert await service.is_editable(appointment.id) is True

    async def test_true_while_cancelled(
        self, service: AppointmentQueryService, repo: FakeAppointmentRepository
    ) -> None:
        appointment = _make_appointment()
        appointment.cancel()
        await repo.add(appointment)
        assert await service.is_editable(appointment.id) is True

    async def test_false_once_completed(
        self, service: AppointmentQueryService, repo: FakeAppointmentRepository
    ) -> None:
        appointment = _make_appointment()
        appointment.check_in()
        appointment.complete()
        await repo.add(appointment)
        assert await service.is_editable(appointment.id) is False

    async def test_false_once_no_show(
        self, service: AppointmentQueryService, repo: FakeAppointmentRepository
    ) -> None:
        appointment = _make_appointment()
        appointment.mark_no_show()
        await repo.add(appointment)
        assert await service.is_editable(appointment.id) is False

    async def test_false_for_an_unknown_appointment(self, service: AppointmentQueryService) -> None:
        assert await service.is_editable(uuid4()) is False


class TestGetAppointmentSummary:
    async def test_returns_summary_for_a_known_appointment(
        self, service: AppointmentQueryService, repo: FakeAppointmentRepository
    ) -> None:
        appointment = _make_appointment(notes="Bring lab results")
        await repo.add(appointment)

        summary = await service.get_appointment_summary(appointment.id)

        assert summary is not None
        assert summary.appointment_id == appointment.id
        assert summary.organization_id == appointment.organization_id
        assert summary.patient_id == appointment.patient_id
        assert summary.doctor_id == appointment.doctor_id
        assert summary.notes == "Bring lab results"

    async def test_returns_none_for_an_unknown_appointment(
        self, service: AppointmentQueryService
    ) -> None:
        assert await service.get_appointment_summary(uuid4()) is None


class TestGetByAppointmentNumber:
    async def test_returns_the_matching_appointment(
        self, service: AppointmentQueryService, repo: FakeAppointmentRepository
    ) -> None:
        appointment = _make_appointment(appointment_number="APT-UNIQUE")
        await repo.add(appointment)

        summary = await service.get_by_appointment_number("APT-UNIQUE")

        assert summary is not None
        assert summary.appointment_id == appointment.id

    async def test_returns_none_for_an_unmatched_number(
        self, service: AppointmentQueryService
    ) -> None:
        assert await service.get_by_appointment_number("APT-MISSING") is None


class TestListAppointmentsForPatient:
    async def test_returns_appointments_ordered_by_date_and_time(
        self, service: AppointmentQueryService, repo: FakeAppointmentRepository
    ) -> None:
        patient_id = uuid4()
        await repo.add(
            _make_appointment(
                patient_id=patient_id,
                appointment_number="APT-2",
                appointment_date=date(2026, 2, 2),
            )
        )
        await repo.add(
            _make_appointment(
                patient_id=patient_id,
                appointment_number="APT-1",
                appointment_date=date(2026, 2, 1),
            )
        )
        await repo.add(_make_appointment(appointment_number="APT-OTHER"))

        summaries = await service.list_appointments_for_patient(patient_id)

        assert [s.appointment_number for s in summaries] == ["APT-1", "APT-2"]

    async def test_returns_empty_list_for_a_patient_without_appointments(
        self, service: AppointmentQueryService
    ) -> None:
        assert await service.list_appointments_for_patient(uuid4()) == []


class TestListAppointmentsForDoctor:
    async def test_returns_appointments_scoped_to_the_doctor(
        self, service: AppointmentQueryService, repo: FakeAppointmentRepository
    ) -> None:
        doctor_id = uuid4()
        await repo.add(_make_appointment(doctor_id=doctor_id, appointment_number="APT-FOR-DOCTOR"))
        await repo.add(_make_appointment(appointment_number="APT-OTHER-DOCTOR"))

        summaries = await service.list_appointments_for_doctor(doctor_id)

        assert [s.appointment_number for s in summaries] == ["APT-FOR-DOCTOR"]

    async def test_returns_empty_list_for_a_doctor_without_appointments(
        self, service: AppointmentQueryService
    ) -> None:
        assert await service.list_appointments_for_doctor(uuid4()) == []
