"""Unit tests for the `UpdateDoctorTimeOff` use case."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.schedule.application.dto import UpdateDoctorTimeOffInput
from app.modules.schedule.application.use_cases.update_doctor_time_off import (
    UpdateDoctorTimeOff,
)
from app.modules.schedule.domain.entities import DoctorTimeOff
from app.modules.schedule.domain.events import DoctorTimeOffUpdated
from app.modules.schedule.domain.exceptions import (
    DoctorTimeOffNotFoundError,
    DoctorTimeOffOverlapError,
    InvalidTimeOffRangeError,
)
from tests.unit.modules.schedule.application.fakes import (
    FakeDoctorTimeOffRepository,
    FakeUnitOfWork,
)


def _make_input(**overrides: object) -> UpdateDoctorTimeOffInput:
    defaults: dict[str, object] = {"time_off_id": uuid4()}
    defaults.update(overrides)
    return UpdateDoctorTimeOffInput(**defaults)  # type: ignore[arg-type]


def _make_time_off(**overrides: object) -> DoctorTimeOff:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "doctor_id": uuid4(),
        "start_datetime": datetime(2026, 6, 1, tzinfo=UTC),
        "end_datetime": datetime(2026, 6, 5, tzinfo=UTC),
    }
    defaults.update(overrides)
    return DoctorTimeOff.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def time_off_repository() -> FakeDoctorTimeOffRepository:
    return FakeDoctorTimeOffRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    time_off_repository: FakeDoctorTimeOffRepository, unit_of_work: FakeUnitOfWork
) -> UpdateDoctorTimeOff:
    return UpdateDoctorTimeOff(
        doctor_time_off_repository=time_off_repository, unit_of_work=unit_of_work
    )


class TestUpdateDoctorTimeOff:
    async def test_updates_fields(
        self, time_off_repository: FakeDoctorTimeOffRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        time_off = _make_time_off()
        await time_off_repository.add(time_off)
        use_case = _use_case(time_off_repository, unit_of_work)

        await use_case.execute(_make_input(time_off_id=time_off.id, reason="Medical leave"))

        stored = await time_off_repository.get_by_id(time_off.id)
        assert stored is not None
        assert stored.reason == "Medical leave"
        assert unit_of_work.committed is True
        assert any(isinstance(e, DoctorTimeOffUpdated) for e in unit_of_work.published_events)

    async def test_unknown_time_off_raises(
        self, time_off_repository: FakeDoctorTimeOffRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(time_off_repository, unit_of_work)
        with pytest.raises(DoctorTimeOffNotFoundError):
            await use_case.execute(_make_input(time_off_id=uuid4()))

    async def test_invalid_range_raises(
        self, time_off_repository: FakeDoctorTimeOffRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        time_off = _make_time_off(
            start_datetime=datetime(2026, 6, 1, tzinfo=UTC),
            end_datetime=datetime(2026, 6, 5, tzinfo=UTC),
        )
        await time_off_repository.add(time_off)
        use_case = _use_case(time_off_repository, unit_of_work)

        with pytest.raises(InvalidTimeOffRangeError):
            await use_case.execute(
                _make_input(
                    time_off_id=time_off.id, start_datetime=datetime(2026, 6, 10, tzinfo=UTC)
                )
            )

    async def test_rescheduling_into_a_siblings_range_raises(
        self, time_off_repository: FakeDoctorTimeOffRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        doctor_id = uuid4()
        sibling = _make_time_off(
            doctor_id=doctor_id,
            start_datetime=datetime(2026, 7, 1, tzinfo=UTC),
            end_datetime=datetime(2026, 7, 10, tzinfo=UTC),
        )
        target = _make_time_off(
            doctor_id=doctor_id,
            start_datetime=datetime(2026, 6, 1, tzinfo=UTC),
            end_datetime=datetime(2026, 6, 5, tzinfo=UTC),
        )
        await time_off_repository.add(sibling)
        await time_off_repository.add(target)
        use_case = _use_case(time_off_repository, unit_of_work)

        with pytest.raises(DoctorTimeOffOverlapError):
            await use_case.execute(
                _make_input(time_off_id=target.id, end_datetime=datetime(2026, 7, 5, tzinfo=UTC))
            )
