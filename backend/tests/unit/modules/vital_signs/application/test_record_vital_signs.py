"""Unit tests for the `RecordVisitVitalSigns` use case, using in-memory
fakes for both this module's own repository and the Visit/Doctor
modules' public ports."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.doctor.domain.exceptions import DoctorNotFoundError
from app.modules.visit.domain.exceptions import PatientVisitNotFoundError
from app.modules.vital_signs.application.dto import RecordVisitVitalSignsInput
from app.modules.vital_signs.application.use_cases.record_vital_signs import (
    RecordVisitVitalSigns,
)
from app.modules.vital_signs.domain.events import VisitVitalSignsRecorded
from app.modules.vital_signs.domain.exceptions import DuplicateVitalSignsForVisitError
from tests.unit.modules.vital_signs.application.fakes import (
    FakeDoctorQueryPort,
    FakeUnitOfWork,
    FakeVisitQueryPort,
    FakeVisitVitalSignsRepository,
)


def _make_input(**overrides: object) -> RecordVisitVitalSignsInput:
    defaults: dict[str, object] = {
        "visit_id": uuid4(),
        "temperature_c": Decimal("37.0"),
        "pulse_bpm": 72,
        "respiratory_rate": 16,
        "systolic_bp": 120,
        "diastolic_bp": 80,
        "spo2": 98,
        "recorded_at": datetime(2026, 1, 1, 9, 0),
    }
    defaults.update(overrides)
    return RecordVisitVitalSignsInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def vital_signs_repository() -> FakeVisitVitalSignsRepository:
    return FakeVisitVitalSignsRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    vital_signs_repository: FakeVisitVitalSignsRepository,
    unit_of_work: FakeUnitOfWork,
    *,
    existing_visits: dict[object, object] | None = None,
    existing_doctors: dict[object, object] | None = None,
) -> RecordVisitVitalSigns:
    return RecordVisitVitalSigns(
        vital_signs_repository=vital_signs_repository,
        visit_query_port=FakeVisitQueryPort(existing_visits=existing_visits),  # type: ignore[arg-type]
        doctor_query_port=FakeDoctorQueryPort(existing_doctors=existing_doctors),  # type: ignore[arg-type]
        unit_of_work=unit_of_work,
    )


class TestRecordVisitVitalSigns:
    async def test_records_vital_signs_for_an_existing_visit(
        self,
        vital_signs_repository: FakeVisitVitalSignsRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        organization_id = uuid4()
        use_case = _use_case(
            vital_signs_repository, unit_of_work, existing_visits={visit_id: organization_id}
        )

        output = await use_case.execute(_make_input(visit_id=visit_id))

        stored = await vital_signs_repository.get_by_visit_id(visit_id)
        assert stored is not None
        assert stored.organization_id == organization_id
        assert output.organization_id == organization_id
        assert unit_of_work.committed is True
        assert any(isinstance(e, VisitVitalSignsRecorded) for e in unit_of_work.published_events)

    async def test_bmi_is_populated_in_output_when_height_and_weight_given(
        self,
        vital_signs_repository: FakeVisitVitalSignsRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        use_case = _use_case(
            vital_signs_repository, unit_of_work, existing_visits={visit_id: uuid4()}
        )

        output = await use_case.execute(
            _make_input(visit_id=visit_id, height_cm=Decimal("170"), weight_kg=Decimal("70"))
        )

        assert output.bmi == Decimal("24.2")

    async def test_unknown_visit_raises(
        self,
        vital_signs_repository: FakeVisitVitalSignsRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = _use_case(vital_signs_repository, unit_of_work)

        with pytest.raises(PatientVisitNotFoundError):
            await use_case.execute(_make_input(visit_id=uuid4()))

    async def test_recorded_by_with_unknown_doctor_raises(
        self,
        vital_signs_repository: FakeVisitVitalSignsRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        use_case = _use_case(
            vital_signs_repository, unit_of_work, existing_visits={visit_id: uuid4()}
        )

        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(_make_input(visit_id=visit_id, recorded_by=uuid4()))

    async def test_recorded_by_doctor_from_a_different_organization_raises(
        self,
        vital_signs_repository: FakeVisitVitalSignsRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        doctor_id = uuid4()
        visit_organization_id = uuid4()
        doctor_organization_id = uuid4()
        use_case = _use_case(
            vital_signs_repository,
            unit_of_work,
            existing_visits={visit_id: visit_organization_id},
            existing_doctors={doctor_id: doctor_organization_id},
        )

        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(_make_input(visit_id=visit_id, recorded_by=doctor_id))

    async def test_recorded_by_doctor_in_the_same_organization_is_accepted(
        self,
        vital_signs_repository: FakeVisitVitalSignsRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        doctor_id = uuid4()
        organization_id = uuid4()
        use_case = _use_case(
            vital_signs_repository,
            unit_of_work,
            existing_visits={visit_id: organization_id},
            existing_doctors={doctor_id: organization_id},
        )

        output = await use_case.execute(_make_input(visit_id=visit_id, recorded_by=doctor_id))

        stored = await vital_signs_repository.get_by_id(output.vital_signs_id)
        assert stored is not None
        assert stored.recorded_by == doctor_id

    async def test_duplicate_vital_signs_for_the_same_visit_is_rejected(
        self,
        vital_signs_repository: FakeVisitVitalSignsRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        use_case = _use_case(
            vital_signs_repository, unit_of_work, existing_visits={visit_id: uuid4()}
        )

        await use_case.execute(_make_input(visit_id=visit_id))

        with pytest.raises(DuplicateVitalSignsForVisitError):
            await use_case.execute(_make_input(visit_id=visit_id))
