"""HTTP-level tests for the Appointment module's router — create, get,
and the confirm -> check-in -> start -> complete status-transition
chain."""

from datetime import date, timedelta
from typing import Any, cast

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organization.domain.entities import Organization
from tests.integration.api._helpers import unique_suffix
from tests.integration.modules.appointment._helpers import persist_doctor, persist_patient

# See `tests.integration.api`'s own `__init__.py` docstring for why this
# must be declared directly in every test module in this package (not
# `__init__.py`, not a `conftest.py` hook).
pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _create_appointment(
    client: AsyncClient, *, patient_id: object, doctor_id: object
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": str(patient_id),
            "doctor_id": str(doctor_id),
            "appointment_number": f"APT-{unique_suffix()}",
            "appointment_date": str(date.today() + timedelta(days=1)),
            "start_time": "09:00:00",
            "end_time": "09:30:00",
            "appointment_type": "consultation",
        },
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


class TestAppointmentLifecycle:
    async def test_create_appointment_returns_201_with_scheduled_status(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_organization: Organization,
    ) -> None:
        patient = await persist_patient(db_session, organization_id=test_organization.id)
        doctor = await persist_doctor(db_session, organization_id=test_organization.id)

        body = await _create_appointment(
            authenticated_client, patient_id=patient.id, doctor_id=doctor.id
        )

        assert body["status"] == "scheduled"
        assert body["patient_id"] == str(patient.id)

    async def test_confirm_check_in_start_complete_transitions(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_organization: Organization,
    ) -> None:
        patient = await persist_patient(db_session, organization_id=test_organization.id)
        doctor = await persist_doctor(db_session, organization_id=test_organization.id)
        appointment = await _create_appointment(
            authenticated_client, patient_id=patient.id, doctor_id=doctor.id
        )
        appointment_id = appointment["id"]

        confirm = await authenticated_client.patch(f"/api/v1/appointments/{appointment_id}/confirm")
        assert confirm.status_code == 200
        assert confirm.json()["status"] == "confirmed"

        check_in = await authenticated_client.patch(
            f"/api/v1/appointments/{appointment_id}/check-in"
        )
        assert check_in.status_code == 200
        assert check_in.json()["status"] == "checked_in"

        start = await authenticated_client.patch(f"/api/v1/appointments/{appointment_id}/start")
        assert start.status_code == 200
        assert start.json()["status"] == "in_progress"

    async def test_cancel_from_scheduled_succeeds(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_organization: Organization,
    ) -> None:
        patient = await persist_patient(db_session, organization_id=test_organization.id)
        doctor = await persist_doctor(db_session, organization_id=test_organization.id)
        appointment = await _create_appointment(
            authenticated_client, patient_id=patient.id, doctor_id=doctor.id
        )

        response = await authenticated_client.patch(
            f"/api/v1/appointments/{appointment['id']}/cancel"
        )

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    async def test_invalid_transition_returns_409(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_organization: Organization,
    ) -> None:
        """Starting an appointment that was never confirmed/checked-in is
        an invalid status transition — the `DomainError` handler maps
        `Transition`-named exceptions to 409 (see
        `app.middlewares.error_handler`'s own docstring)."""
        patient = await persist_patient(db_session, organization_id=test_organization.id)
        doctor = await persist_doctor(db_session, organization_id=test_organization.id)
        appointment = await _create_appointment(
            authenticated_client, patient_id=patient.id, doctor_id=doctor.id
        )

        response = await authenticated_client.patch(
            f"/api/v1/appointments/{appointment['id']}/start"
        )

        assert response.status_code == 409

    async def test_get_appointment_by_number(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_organization: Organization,
    ) -> None:
        patient = await persist_patient(db_session, organization_id=test_organization.id)
        doctor = await persist_doctor(db_session, organization_id=test_organization.id)
        appointment = await _create_appointment(
            authenticated_client, patient_id=patient.id, doctor_id=doctor.id
        )

        response = await authenticated_client.get(
            f"/api/v1/appointments/by-number/{appointment['appointment_number']}"
        )

        assert response.status_code == 200
        assert response.json()["id"] == appointment["id"]
