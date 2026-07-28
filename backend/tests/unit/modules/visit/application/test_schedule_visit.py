"""Unit tests for the `ScheduleVisit` use case, using in-memory fakes for
both this module's own repository and the Patient/Doctor modules' public
ports."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.doctor.domain.exceptions import DoctorNotFoundError
from app.modules.patient.domain.exceptions import PatientNotFoundError
from app.modules.visit.application.dto import ScheduleVisitInput
from app.modules.visit.application.use_cases.schedule_visit import ScheduleVisit
from app.modules.visit.domain.enums import VisitStatus, VisitType
from app.modules.visit.domain.events import PatientVisitScheduled
from app.modules.visit.domain.exceptions import DuplicateVisitNumberError
from tests.unit.modules.visit.application.fakes import (
    FakeDoctorQueryPort,
    FakePatientQueryPort,
    FakePatientVisitRepository,
    FakeUnitOfWork,
)


def _make_input(**overrides: object) -> ScheduleVisitInput:
    defaults: dict[str, object] = {
        "patient_id": uuid4(),
        "doctor_id": uuid4(),
        "visit_number": "V-0001",
        "visit_type": VisitType.CONSULTATION,
        "visit_date": date(2026, 1, 1),
    }
    defaults.update(overrides)
    return ScheduleVisitInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def patient_visit_repository() -> FakePatientVisitRepository:
    return FakePatientVisitRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    patient_visit_repository: FakePatientVisitRepository,
    unit_of_work: FakeUnitOfWork,
    *,
    existing_patients: dict[object, object] | None = None,
    existing_doctors: dict[object, object] | None = None,
) -> ScheduleVisit:
    return ScheduleVisit(
        patient_visit_repository=patient_visit_repository,
        patient_query_port=FakePatientQueryPort(
            existing_patients=existing_patients  # type: ignore[arg-type]
        ),
        doctor_query_port=FakeDoctorQueryPort(
            existing_doctors=existing_doctors  # type: ignore[arg-type]
        ),
        unit_of_work=unit_of_work,
    )


class TestScheduleVisit:
    async def test_schedules_visit_for_existing_patient_and_doctor(
        self,
        patient_visit_repository: FakePatientVisitRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient_id = uuid4()
        doctor_id = uuid4()
        organization_id = uuid4()
        use_case = _use_case(
            patient_visit_repository,
            unit_of_work,
            existing_patients={patient_id: organization_id},
            existing_doctors={doctor_id: organization_id},
        )

        output = await use_case.execute(_make_input(patient_id=patient_id, doctor_id=doctor_id))

        stored = await patient_visit_repository.get_by_id(output.visit_id)
        assert stored is not None
        assert stored.organization_id == organization_id
        assert stored.visit_status is VisitStatus.SCHEDULED
        assert unit_of_work.committed is True
        assert any(isinstance(e, PatientVisitScheduled) for e in unit_of_work.published_events)

    async def test_unknown_patient_raises(
        self,
        patient_visit_repository: FakePatientVisitRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        doctor_id = uuid4()
        organization_id = uuid4()
        use_case = _use_case(
            patient_visit_repository,
            unit_of_work,
            existing_doctors={doctor_id: organization_id},
        )

        with pytest.raises(PatientNotFoundError):
            await use_case.execute(_make_input(patient_id=uuid4(), doctor_id=doctor_id))

    async def test_unknown_doctor_raises(
        self,
        patient_visit_repository: FakePatientVisitRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient_id = uuid4()
        organization_id = uuid4()
        use_case = _use_case(
            patient_visit_repository,
            unit_of_work,
            existing_patients={patient_id: organization_id},
        )

        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(_make_input(patient_id=patient_id, doctor_id=uuid4()))

    async def test_doctor_from_a_different_organization_raises(
        self,
        patient_visit_repository: FakePatientVisitRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient_id = uuid4()
        doctor_id = uuid4()
        patient_organization_id = uuid4()
        doctor_organization_id = uuid4()
        use_case = _use_case(
            patient_visit_repository,
            unit_of_work,
            existing_patients={patient_id: patient_organization_id},
            existing_doctors={doctor_id: doctor_organization_id},
        )

        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(_make_input(patient_id=patient_id, doctor_id=doctor_id))

    async def test_duplicate_visit_number_within_organization_is_rejected(
        self,
        patient_visit_repository: FakePatientVisitRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        organization_id = uuid4()
        first_patient_id = uuid4()
        second_patient_id = uuid4()
        doctor_id = uuid4()
        use_case = _use_case(
            patient_visit_repository,
            unit_of_work,
            existing_patients={
                first_patient_id: organization_id,
                second_patient_id: organization_id,
            },
            existing_doctors={doctor_id: organization_id},
        )

        await use_case.execute(
            _make_input(patient_id=first_patient_id, doctor_id=doctor_id, visit_number="V-0001")
        )

        with pytest.raises(DuplicateVisitNumberError):
            await use_case.execute(
                _make_input(
                    patient_id=second_patient_id, doctor_id=doctor_id, visit_number="V-0001"
                )
            )

    async def test_same_visit_number_in_different_organizations_is_allowed(
        self,
        patient_visit_repository: FakePatientVisitRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        org_a = uuid4()
        org_b = uuid4()
        patient_a = uuid4()
        patient_b = uuid4()
        doctor_a = uuid4()
        doctor_b = uuid4()
        use_case = _use_case(
            patient_visit_repository,
            unit_of_work,
            existing_patients={patient_a: org_a, patient_b: org_b},
            existing_doctors={doctor_a: org_a, doctor_b: org_b},
        )

        await use_case.execute(
            _make_input(patient_id=patient_a, doctor_id=doctor_a, visit_number="V-0001")
        )
        output_b = await use_case.execute(
            _make_input(patient_id=patient_b, doctor_id=doctor_b, visit_number="V-0001")
        )

        stored_b = await patient_visit_repository.get_by_id(output_b.visit_id)
        assert stored_b is not None
        assert stored_b.organization_id == org_b
