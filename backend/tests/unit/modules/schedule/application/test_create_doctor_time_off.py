"""Unit tests for the `CreateDoctorTimeOff` use case, using in-memory
fakes for this module's own repository and the Doctor module's public
port (via `ScheduleConsistencyService`)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.schedule.application.dto import CreateDoctorTimeOffInput
from app.modules.schedule.application.services.schedule_consistency_service import (
    ScheduleConsistencyService,
)
from app.modules.schedule.application.use_cases.create_doctor_time_off import (
    CreateDoctorTimeOff,
)
from app.modules.schedule.domain.events import DoctorTimeOffCreated
from app.modules.schedule.domain.exceptions import DoctorNotFoundError, DoctorTimeOffOverlapError
from tests.unit.modules.schedule.application.fakes import (
    FakeDoctorQueryPort,
    FakeDoctorTimeOffRepository,
    FakeUnitOfWork,
    make_doctor_summary,
)


def _make_input(**overrides: object) -> CreateDoctorTimeOffInput:
    defaults: dict[str, object] = {
        "doctor_id": uuid4(),
        "start_datetime": datetime(2026, 6, 1, tzinfo=UTC),
        "end_datetime": datetime(2026, 6, 5, tzinfo=UTC),
    }
    defaults.update(overrides)
    return CreateDoctorTimeOffInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def time_off_repository() -> FakeDoctorTimeOffRepository:
    return FakeDoctorTimeOffRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    time_off_repository: FakeDoctorTimeOffRepository,
    unit_of_work: FakeUnitOfWork,
    doctor_query_port: FakeDoctorQueryPort,
) -> CreateDoctorTimeOff:
    return CreateDoctorTimeOff(
        doctor_time_off_repository=time_off_repository,
        consistency_service=ScheduleConsistencyService(doctor_query_port=doctor_query_port),
        unit_of_work=unit_of_work,
    )


class TestCreateDoctorTimeOff:
    async def test_creates_time_off_with_derived_organization_id(
        self, time_off_repository: FakeDoctorTimeOffRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        organization_id = uuid4()
        doctor_id = uuid4()
        doctor_port = FakeDoctorQueryPort(
            existing_doctors={
                doctor_id: make_doctor_summary(doctor_id=doctor_id, organization_id=organization_id)
            }
        )
        use_case = _use_case(time_off_repository, unit_of_work, doctor_port)

        output = await use_case.execute(_make_input(doctor_id=doctor_id))

        assert output.organization_id == organization_id
        stored = await time_off_repository.get_by_id(output.time_off_id)
        assert stored is not None
        assert stored.doctor_id == doctor_id
        assert unit_of_work.committed is True
        assert any(isinstance(e, DoctorTimeOffCreated) for e in unit_of_work.published_events)

    async def test_unknown_doctor_raises(
        self, time_off_repository: FakeDoctorTimeOffRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(time_off_repository, unit_of_work, FakeDoctorQueryPort())
        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(_make_input())

    async def test_non_overlapping_periods_are_allowed(
        self, time_off_repository: FakeDoctorTimeOffRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        doctor_id = uuid4()
        doctor_port = FakeDoctorQueryPort(
            existing_doctors={doctor_id: make_doctor_summary(doctor_id=doctor_id)}
        )
        use_case = _use_case(time_off_repository, unit_of_work, doctor_port)
        await use_case.execute(
            _make_input(
                doctor_id=doctor_id,
                start_datetime=datetime(2026, 6, 1, tzinfo=UTC),
                end_datetime=datetime(2026, 6, 5, tzinfo=UTC),
            )
        )

        output = await use_case.execute(
            _make_input(
                doctor_id=doctor_id,
                start_datetime=datetime(2026, 7, 1, tzinfo=UTC),
                end_datetime=datetime(2026, 7, 5, tzinfo=UTC),
            )
        )

        stored = await time_off_repository.get_by_id(output.time_off_id)
        assert stored is not None

    async def test_overlapping_periods_raise(
        self, time_off_repository: FakeDoctorTimeOffRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        doctor_id = uuid4()
        doctor_port = FakeDoctorQueryPort(
            existing_doctors={doctor_id: make_doctor_summary(doctor_id=doctor_id)}
        )
        use_case = _use_case(time_off_repository, unit_of_work, doctor_port)
        await use_case.execute(
            _make_input(
                doctor_id=doctor_id,
                start_datetime=datetime(2026, 6, 1, tzinfo=UTC),
                end_datetime=datetime(2026, 6, 10, tzinfo=UTC),
            )
        )

        with pytest.raises(DoctorTimeOffOverlapError):
            await use_case.execute(
                _make_input(
                    doctor_id=doctor_id,
                    start_datetime=datetime(2026, 6, 5, tzinfo=UTC),
                    end_datetime=datetime(2026, 6, 15, tzinfo=UTC),
                )
            )

    async def test_overlapping_periods_for_different_doctors_are_allowed(
        self, time_off_repository: FakeDoctorTimeOffRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        doctor_a = uuid4()
        doctor_b = uuid4()
        doctor_port = FakeDoctorQueryPort(
            existing_doctors={
                doctor_a: make_doctor_summary(doctor_id=doctor_a),
                doctor_b: make_doctor_summary(doctor_id=doctor_b),
            }
        )
        use_case = _use_case(time_off_repository, unit_of_work, doctor_port)
        await use_case.execute(
            _make_input(
                doctor_id=doctor_a,
                start_datetime=datetime(2026, 6, 1, tzinfo=UTC),
                end_datetime=datetime(2026, 6, 10, tzinfo=UTC),
            )
        )

        output = await use_case.execute(
            _make_input(
                doctor_id=doctor_b,
                start_datetime=datetime(2026, 6, 5, tzinfo=UTC),
                end_datetime=datetime(2026, 6, 15, tzinfo=UTC),
            )
        )

        stored = await time_off_repository.get_by_id(output.time_off_id)
        assert stored is not None
