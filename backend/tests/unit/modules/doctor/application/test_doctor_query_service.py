"""Unit tests for `DoctorQueryService` — backs the module's public
`DoctorQueryPort` facade."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.doctor.application.services.doctor_query_service import DoctorQueryService
from app.modules.doctor.domain.entities import Doctor
from tests.unit.modules.doctor.application.fakes import FakeDoctorRepository


def _make_doctor(**overrides: object) -> Doctor:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "user_id": uuid4(),
        "employee_id": "EMP-001",
        "joining_date": date(2026, 1, 1),
    }
    defaults.update(overrides)
    return Doctor.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def doctor_repository() -> FakeDoctorRepository:
    return FakeDoctorRepository()


@pytest.fixture
def service(doctor_repository: FakeDoctorRepository) -> DoctorQueryService:
    return DoctorQueryService(doctor_repository=doctor_repository)


class TestDoctorExists:
    async def test_true_for_a_known_doctor(
        self, service: DoctorQueryService, doctor_repository: FakeDoctorRepository
    ) -> None:
        doctor = _make_doctor()
        await doctor_repository.add(doctor)
        assert await service.doctor_exists(doctor.id) is True

    async def test_false_for_an_unknown_doctor(self, service: DoctorQueryService) -> None:
        assert await service.doctor_exists(uuid4()) is False


class TestIsActive:
    async def test_reflects_the_doctors_status(
        self, service: DoctorQueryService, doctor_repository: FakeDoctorRepository
    ) -> None:
        doctor = _make_doctor()
        await doctor_repository.add(doctor)
        assert await service.is_active(doctor.id) is True

        doctor.deactivate()
        await doctor_repository.add(doctor)
        assert await service.is_active(doctor.id) is False

    async def test_false_for_an_unknown_doctor(self, service: DoctorQueryService) -> None:
        assert await service.is_active(uuid4()) is False


class TestGetDoctorSummary:
    async def test_returns_summary_for_known_doctor(
        self, service: DoctorQueryService, doctor_repository: FakeDoctorRepository
    ) -> None:
        doctor = _make_doctor(employee_id="EMP-42")
        await doctor_repository.add(doctor)

        summary = await service.get_doctor_summary(doctor.id)

        assert summary is not None
        assert summary.employee_id == "EMP-42"
        assert summary.organization_id == doctor.organization_id
        assert summary.user_id == doctor.user_id

    async def test_returns_none_for_unknown_doctor(self, service: DoctorQueryService) -> None:
        assert await service.get_doctor_summary(uuid4()) is None
