"""Unit tests for `AppointmentConsistencyService` — "Organization
consistency" and "Foreign keys" validation for `patient_id`/`doctor_id`,
`booked_by_user_id`, and `visit_id`."""

from uuid import uuid4

import pytest

from app.modules.appointment.application.services.appointment_consistency_service import (
    AppointmentConsistencyService,
)
from app.modules.appointment.domain.exceptions import (
    AppointmentVisitMismatchError,
    AppointmentVisitNotFoundError,
    BookedByUserNotFoundError,
    BookedByUserOrganizationMismatchError,
    DoctorNotFoundError,
    PatientDoctorOrganizationMismatchError,
    PatientNotFoundError,
)
from tests.unit.modules.appointment.application.fakes import (
    FakeDoctorQueryPort,
    FakePatientQueryPort,
    FakeUserQueryPort,
    FakeVisitQueryPort,
    make_doctor_summary,
    make_patient_summary,
    make_user_summary,
    make_visit_summary,
)


def _service(
    *,
    patient_query_port: FakePatientQueryPort | None = None,
    doctor_query_port: FakeDoctorQueryPort | None = None,
    user_query_port: FakeUserQueryPort | None = None,
    visit_query_port: FakeVisitQueryPort | None = None,
) -> AppointmentConsistencyService:
    return AppointmentConsistencyService(
        patient_query_port=patient_query_port or FakePatientQueryPort(),
        doctor_query_port=doctor_query_port or FakeDoctorQueryPort(),
        user_query_port=user_query_port or FakeUserQueryPort(),
        visit_query_port=visit_query_port or FakeVisitQueryPort(),
    )


class TestResolveAndValidateOrganization:
    async def test_returns_the_shared_organization_id(self) -> None:
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
        service = _service(patient_query_port=patient_port, doctor_query_port=doctor_port)

        result = await service.resolve_and_validate_organization(
            patient_id=patient_id, doctor_id=doctor_id
        )

        assert result == organization_id

    async def test_unknown_patient_raises(self) -> None:
        with pytest.raises(PatientNotFoundError):
            await _service().resolve_and_validate_organization(
                patient_id=uuid4(), doctor_id=uuid4()
            )

    async def test_unknown_doctor_raises(self) -> None:
        patient_id = uuid4()
        patient_port = FakePatientQueryPort(
            existing_patients={patient_id: make_patient_summary(patient_id=patient_id)}
        )
        with pytest.raises(DoctorNotFoundError):
            await _service(patient_query_port=patient_port).resolve_and_validate_organization(
                patient_id=patient_id, doctor_id=uuid4()
            )

    async def test_mismatched_organizations_raise(self) -> None:
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
        service = _service(patient_query_port=patient_port, doctor_query_port=doctor_port)

        with pytest.raises(PatientDoctorOrganizationMismatchError):
            await service.resolve_and_validate_organization(
                patient_id=patient_id, doctor_id=doctor_id
            )


class TestValidateBookedByUser:
    async def test_none_is_always_valid(self) -> None:
        await _service().validate_booked_by_user(booked_by_user_id=None, organization_id=uuid4())

    async def test_matching_user_passes(self) -> None:
        organization_id = uuid4()
        user_id = uuid4()
        port = FakeUserQueryPort(
            existing_users={
                user_id: make_user_summary(user_id=user_id, organization_id=organization_id)
            }
        )
        await _service(user_query_port=port).validate_booked_by_user(
            booked_by_user_id=user_id, organization_id=organization_id
        )

    async def test_unknown_user_raises(self) -> None:
        with pytest.raises(BookedByUserNotFoundError):
            await _service().validate_booked_by_user(
                booked_by_user_id=uuid4(), organization_id=uuid4()
            )

    async def test_mismatched_organization_raises(self) -> None:
        user_id = uuid4()
        port = FakeUserQueryPort(
            existing_users={user_id: make_user_summary(user_id=user_id, organization_id=uuid4())}
        )
        with pytest.raises(BookedByUserOrganizationMismatchError):
            await _service(user_query_port=port).validate_booked_by_user(
                booked_by_user_id=user_id, organization_id=uuid4()
            )


class TestValidateVisitForCompletion:
    async def test_none_is_always_valid(self) -> None:
        await _service().validate_visit_for_completion(
            visit_id=None, organization_id=uuid4(), patient_id=uuid4(), doctor_id=uuid4()
        )

    async def test_matching_visit_passes(self) -> None:
        organization_id = uuid4()
        patient_id = uuid4()
        doctor_id = uuid4()
        visit_id = uuid4()
        port = FakeVisitQueryPort(
            existing_visits={
                visit_id: make_visit_summary(
                    visit_id=visit_id,
                    organization_id=organization_id,
                    patient_id=patient_id,
                    doctor_id=doctor_id,
                )
            }
        )
        await _service(visit_query_port=port).validate_visit_for_completion(
            visit_id=visit_id,
            organization_id=organization_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
        )

    async def test_unknown_visit_raises(self) -> None:
        with pytest.raises(AppointmentVisitNotFoundError):
            await _service().validate_visit_for_completion(
                visit_id=uuid4(), organization_id=uuid4(), patient_id=uuid4(), doctor_id=uuid4()
            )

    async def test_mismatched_patient_raises(self) -> None:
        organization_id = uuid4()
        doctor_id = uuid4()
        visit_id = uuid4()
        port = FakeVisitQueryPort(
            existing_visits={
                visit_id: make_visit_summary(
                    visit_id=visit_id,
                    organization_id=organization_id,
                    patient_id=uuid4(),
                    doctor_id=doctor_id,
                )
            }
        )
        with pytest.raises(AppointmentVisitMismatchError):
            await _service(visit_query_port=port).validate_visit_for_completion(
                visit_id=visit_id,
                organization_id=organization_id,
                patient_id=uuid4(),
                doctor_id=doctor_id,
            )
