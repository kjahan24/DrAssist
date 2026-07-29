"""Unit tests for the `RecordVisitChiefComplaint` use case, using
in-memory fakes for both this module's own repository and the
Visit/Doctor modules' public ports."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.modules.chief_complaints.application.dto import RecordVisitChiefComplaintInput
from app.modules.chief_complaints.application.use_cases.record_chief_complaint import (
    RecordVisitChiefComplaint,
)
from app.modules.chief_complaints.domain.events import VisitChiefComplaintRecorded
from app.modules.chief_complaints.domain.exceptions import DuplicateSequenceNumberError
from app.modules.doctor.domain.exceptions import DoctorNotFoundError
from app.modules.visit.domain.exceptions import PatientVisitNotFoundError
from tests.unit.modules.chief_complaints.application.fakes import (
    FakeDoctorQueryPort,
    FakeUnitOfWork,
    FakeVisitChiefComplaintRepository,
    FakeVisitQueryPort,
)


def _make_input(**overrides: object) -> RecordVisitChiefComplaintInput:
    defaults: dict[str, object] = {
        "visit_id": uuid4(),
        "sequence_number": 1,
        "complaint": "Persistent cough",
        "recorded_at": datetime(2026, 1, 1, 9, 0),
    }
    defaults.update(overrides)
    return RecordVisitChiefComplaintInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def chief_complaint_repository() -> FakeVisitChiefComplaintRepository:
    return FakeVisitChiefComplaintRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    chief_complaint_repository: FakeVisitChiefComplaintRepository,
    unit_of_work: FakeUnitOfWork,
    *,
    existing_visits: dict[object, object] | None = None,
    existing_doctors: dict[object, object] | None = None,
) -> RecordVisitChiefComplaint:
    return RecordVisitChiefComplaint(
        chief_complaint_repository=chief_complaint_repository,
        visit_query_port=FakeVisitQueryPort(existing_visits=existing_visits),  # type: ignore[arg-type]
        doctor_query_port=FakeDoctorQueryPort(existing_doctors=existing_doctors),  # type: ignore[arg-type]
        unit_of_work=unit_of_work,
    )


class TestRecordVisitChiefComplaint:
    async def test_records_a_chief_complaint_for_an_existing_visit(
        self,
        chief_complaint_repository: FakeVisitChiefComplaintRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        organization_id = uuid4()
        use_case = _use_case(
            chief_complaint_repository, unit_of_work, existing_visits={visit_id: organization_id}
        )

        output = await use_case.execute(_make_input(visit_id=visit_id))

        stored = await chief_complaint_repository.get_by_id(output.chief_complaint_id)
        assert stored is not None
        assert stored.organization_id == organization_id
        assert output.sequence_number == 1
        assert unit_of_work.committed is True
        assert any(
            isinstance(e, VisitChiefComplaintRecorded) for e in unit_of_work.published_events
        )

    async def test_unknown_visit_raises(
        self,
        chief_complaint_repository: FakeVisitChiefComplaintRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = _use_case(chief_complaint_repository, unit_of_work)

        with pytest.raises(PatientVisitNotFoundError):
            await use_case.execute(_make_input(visit_id=uuid4()))

    async def test_recorded_by_with_unknown_doctor_raises(
        self,
        chief_complaint_repository: FakeVisitChiefComplaintRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        use_case = _use_case(
            chief_complaint_repository, unit_of_work, existing_visits={visit_id: uuid4()}
        )

        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(_make_input(visit_id=visit_id, recorded_by=uuid4()))

    async def test_recorded_by_doctor_from_a_different_organization_raises(
        self,
        chief_complaint_repository: FakeVisitChiefComplaintRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        doctor_id = uuid4()
        visit_organization_id = uuid4()
        doctor_organization_id = uuid4()
        use_case = _use_case(
            chief_complaint_repository,
            unit_of_work,
            existing_visits={visit_id: visit_organization_id},
            existing_doctors={doctor_id: doctor_organization_id},
        )

        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(_make_input(visit_id=visit_id, recorded_by=doctor_id))

    async def test_recorded_by_doctor_in_the_same_organization_is_accepted(
        self,
        chief_complaint_repository: FakeVisitChiefComplaintRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        doctor_id = uuid4()
        organization_id = uuid4()
        use_case = _use_case(
            chief_complaint_repository,
            unit_of_work,
            existing_visits={visit_id: organization_id},
            existing_doctors={doctor_id: organization_id},
        )

        output = await use_case.execute(_make_input(visit_id=visit_id, recorded_by=doctor_id))

        stored = await chief_complaint_repository.get_by_id(output.chief_complaint_id)
        assert stored is not None
        assert stored.recorded_by == doctor_id

    async def test_duplicate_sequence_number_within_the_same_visit_is_rejected(
        self,
        chief_complaint_repository: FakeVisitChiefComplaintRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        use_case = _use_case(
            chief_complaint_repository, unit_of_work, existing_visits={visit_id: uuid4()}
        )

        await use_case.execute(_make_input(visit_id=visit_id, sequence_number=1))

        with pytest.raises(DuplicateSequenceNumberError):
            await use_case.execute(_make_input(visit_id=visit_id, sequence_number=1))

    async def test_same_sequence_number_on_different_visits_is_allowed(
        self,
        chief_complaint_repository: FakeVisitChiefComplaintRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_a = uuid4()
        visit_b = uuid4()
        use_case = _use_case(
            chief_complaint_repository,
            unit_of_work,
            existing_visits={visit_a: uuid4(), visit_b: uuid4()},
        )

        await use_case.execute(_make_input(visit_id=visit_a, sequence_number=1))
        output_b = await use_case.execute(_make_input(visit_id=visit_b, sequence_number=1))

        stored_b = await chief_complaint_repository.get_by_id(output_b.chief_complaint_id)
        assert stored_b is not None
        assert stored_b.visit_id == visit_b

    async def test_second_complaint_for_the_same_visit_with_new_sequence_is_allowed(
        self,
        chief_complaint_repository: FakeVisitChiefComplaintRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        use_case = _use_case(
            chief_complaint_repository, unit_of_work, existing_visits={visit_id: uuid4()}
        )

        await use_case.execute(_make_input(visit_id=visit_id, sequence_number=1))
        output_2 = await use_case.execute(_make_input(visit_id=visit_id, sequence_number=2))

        stored = await chief_complaint_repository.list_by_visit(visit_id)
        assert [c.sequence_number for c in stored] == [1, 2]
        assert output_2.sequence_number == 2
