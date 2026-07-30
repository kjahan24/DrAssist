"""Unit tests for the `CreateAppointment` use case, using in-memory
fakes for this module's own repository and `AppointmentConsistencyService`
(backed by its own fakes for the peer-module ports)."""

from datetime import date, time
from uuid import uuid4

import pytest

from app.modules.appointment.application.dto import CreateAppointmentInput
from app.modules.appointment.application.services.appointment_consistency_service import (
    AppointmentConsistencyService,
)
from app.modules.appointment.application.use_cases.create_appointment import CreateAppointment
from app.modules.appointment.domain.enums import AppointmentStatus, AppointmentType
from app.modules.appointment.domain.events import AppointmentCreated
from app.modules.appointment.domain.exceptions import (
    BookedByUserNotFoundError,
    DoctorNotFoundError,
    DuplicateAppointmentNumberError,
    PatientDoctorOrganizationMismatchError,
    PatientNotFoundError,
)
from tests.unit.modules.appointment.application.fakes import (
    FakeAppointmentRepository,
    FakeDoctorQueryPort,
    FakePatientQueryPort,
    FakeUnitOfWork,
    FakeUserQueryPort,
    FakeVisitQueryPort,
    make_doctor_summary,
    make_patient_summary,
    make_user_summary,
)


def _make_input(**overrides: object) -> CreateAppointmentInput:
    defaults: dict[str, object] = {
        "patient_id": uuid4(),
        "doctor_id": uuid4(),
        "appointment_number": "APT-0001",
        "appointment_date": date(2026, 2, 1),
        "start_time": time(9, 0),
        "end_time": time(9, 30),
        "appointment_type": AppointmentType.CONSULTATION,
    }
    defaults.update(overrides)
    return CreateAppointmentInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def appointment_repository() -> FakeAppointmentRepository:
    return FakeAppointmentRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    appointment_repository: FakeAppointmentRepository,
    unit_of_work: FakeUnitOfWork,
    patient_query_port: FakePatientQueryPort,
    doctor_query_port: FakeDoctorQueryPort,
    user_query_port: FakeUserQueryPort | None = None,
) -> CreateAppointment:
    consistency_service = AppointmentConsistencyService(
        patient_query_port=patient_query_port,
        doctor_query_port=doctor_query_port,
        user_query_port=user_query_port or FakeUserQueryPort(),
        visit_query_port=FakeVisitQueryPort(),
    )
    return CreateAppointment(
        appointment_repository=appointment_repository,
        consistency_service=consistency_service,
        unit_of_work=unit_of_work,
    )


class TestCreateAppointment:
    async def test_creates_appointment_starting_scheduled(
        self,
        appointment_repository: FakeAppointmentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        organization_id = uuid4()
        patient_id = uuid4()
        doctor_id = uuid4()
        patient_port = FakePatientQueryPort(
            existing_patients={
                patient_id: make_patient_summary(
                    patient_id=patient_id, organization_id=organization_id
                )
            }
        )
        doctor_port = FakeDoctorQueryPort(
            existing_doctors={
                doctor_id: make_doctor_summary(doctor_id=doctor_id, organization_id=organization_id)
            }
        )
        use_case = _use_case(appointment_repository, unit_of_work, patient_port, doctor_port)

        output = await use_case.execute(_make_input(patient_id=patient_id, doctor_id=doctor_id))

        assert output.status is AppointmentStatus.SCHEDULED
        assert output.organization_id == organization_id
        stored = await appointment_repository.get_by_id(output.appointment_id)
        assert stored is not None
        assert stored.patient_id == patient_id
        assert stored.doctor_id == doctor_id
        assert unit_of_work.committed is True
        assert any(isinstance(e, AppointmentCreated) for e in unit_of_work.published_events)

    async def test_unknown_patient_raises(
        self,
        appointment_repository: FakeAppointmentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = _use_case(
            appointment_repository, unit_of_work, FakePatientQueryPort(), FakeDoctorQueryPort()
        )

        with pytest.raises(PatientNotFoundError):
            await use_case.execute(_make_input())

    async def test_unknown_doctor_raises(
        self,
        appointment_repository: FakeAppointmentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient_id = uuid4()
        patient_port = FakePatientQueryPort(
            existing_patients={patient_id: make_patient_summary(patient_id=patient_id)}
        )
        use_case = _use_case(
            appointment_repository, unit_of_work, patient_port, FakeDoctorQueryPort()
        )

        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(_make_input(patient_id=patient_id))

    async def test_patient_and_doctor_in_different_organizations_raises(
        self,
        appointment_repository: FakeAppointmentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient_id = uuid4()
        doctor_id = uuid4()
        patient_port = FakePatientQueryPort(
            existing_patients={
                patient_id: make_patient_summary(patient_id=patient_id, organization_id=uuid4())
            }
        )
        doctor_port = FakeDoctorQueryPort(
            existing_doctors={
                doctor_id: make_doctor_summary(doctor_id=doctor_id, organization_id=uuid4())
            }
        )
        use_case = _use_case(appointment_repository, unit_of_work, patient_port, doctor_port)

        with pytest.raises(PatientDoctorOrganizationMismatchError):
            await use_case.execute(_make_input(patient_id=patient_id, doctor_id=doctor_id))

    async def test_unknown_booked_by_user_raises(
        self,
        appointment_repository: FakeAppointmentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        organization_id = uuid4()
        patient_id = uuid4()
        doctor_id = uuid4()
        patient_port = FakePatientQueryPort(
            existing_patients={
                patient_id: make_patient_summary(
                    patient_id=patient_id, organization_id=organization_id
                )
            }
        )
        doctor_port = FakeDoctorQueryPort(
            existing_doctors={
                doctor_id: make_doctor_summary(doctor_id=doctor_id, organization_id=organization_id)
            }
        )
        use_case = _use_case(appointment_repository, unit_of_work, patient_port, doctor_port)

        with pytest.raises(BookedByUserNotFoundError):
            await use_case.execute(
                _make_input(patient_id=patient_id, doctor_id=doctor_id, booked_by_user_id=uuid4())
            )

    async def test_valid_booked_by_user_is_accepted(
        self,
        appointment_repository: FakeAppointmentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        organization_id = uuid4()
        patient_id = uuid4()
        doctor_id = uuid4()
        booked_by_user_id = uuid4()
        patient_port = FakePatientQueryPort(
            existing_patients={
                patient_id: make_patient_summary(
                    patient_id=patient_id, organization_id=organization_id
                )
            }
        )
        doctor_port = FakeDoctorQueryPort(
            existing_doctors={
                doctor_id: make_doctor_summary(doctor_id=doctor_id, organization_id=organization_id)
            }
        )
        user_port = FakeUserQueryPort(
            existing_users={
                booked_by_user_id: make_user_summary(
                    user_id=booked_by_user_id, organization_id=organization_id
                )
            }
        )
        use_case = _use_case(
            appointment_repository, unit_of_work, patient_port, doctor_port, user_port
        )

        output = await use_case.execute(
            _make_input(
                patient_id=patient_id,
                doctor_id=doctor_id,
                booked_by_user_id=booked_by_user_id,
            )
        )

        stored = await appointment_repository.get_by_id(output.appointment_id)
        assert stored is not None
        assert stored.booked_by_user_id == booked_by_user_id

    async def test_duplicate_appointment_number_raises(
        self,
        appointment_repository: FakeAppointmentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        organization_id = uuid4()
        patient_a, patient_b = uuid4(), uuid4()
        doctor_a, doctor_b = uuid4(), uuid4()
        patient_port = FakePatientQueryPort(
            existing_patients={
                patient_a: make_patient_summary(
                    patient_id=patient_a, organization_id=organization_id
                ),
                patient_b: make_patient_summary(
                    patient_id=patient_b, organization_id=organization_id
                ),
            }
        )
        doctor_port = FakeDoctorQueryPort(
            existing_doctors={
                doctor_a: make_doctor_summary(doctor_id=doctor_a, organization_id=organization_id),
                doctor_b: make_doctor_summary(doctor_id=doctor_b, organization_id=organization_id),
            }
        )
        use_case = _use_case(appointment_repository, unit_of_work, patient_port, doctor_port)
        await use_case.execute(
            _make_input(patient_id=patient_a, doctor_id=doctor_a, appointment_number="APT-DUP")
        )

        with pytest.raises(DuplicateAppointmentNumberError):
            await use_case.execute(
                _make_input(patient_id=patient_b, doctor_id=doctor_b, appointment_number="APT-DUP")
            )
