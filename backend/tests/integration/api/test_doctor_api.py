"""HTTP-level tests for the Doctor module's router — onboarding (which
creates both `Doctor` and its `DoctorProfile` in one transaction) and the
license/specialization/schedule sub-resources."""

import pytest
from httpx import AsyncClient

from app.modules.authentication.domain.entities import User
from tests.integration.api._helpers import unique_suffix

# See `tests.integration.api`'s own `__init__.py` docstring for why this
# must be declared directly in every test module in this package (not
# `__init__.py`, not a `conftest.py` hook).
pytestmark = pytest.mark.asyncio(loop_scope="session")


def _onboard_doctor_payload(user_id: object, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "user_id": str(user_id),
        "employee_id": f"EMP-{unique_suffix()}",
        "joining_date": "2020-01-01",
        "full_name": "Dr. Alice Smith",
        "gender": "female",
        "date_of_birth": "1980-01-01",
    }
    payload.update(overrides)
    return payload


class TestOnboardDoctor:
    async def test_onboard_doctor_returns_201(
        self, authenticated_client: AsyncClient, test_user: User
    ) -> None:
        response = await authenticated_client.post(
            "/api/v1/doctors", json=_onboard_doctor_payload(test_user.id)
        )

        assert response.status_code == 201
        body = response.json()
        assert body["employee_id"].startswith("EMP-")
        assert body["status"] == "active"
        assert "id" in body

    async def test_onboarding_creates_profile(
        self, authenticated_client: AsyncClient, test_user: User
    ) -> None:
        create_response = await authenticated_client.post(
            "/api/v1/doctors", json=_onboard_doctor_payload(test_user.id)
        )
        doctor_id = create_response.json()["id"]

        profile_response = await authenticated_client.get(f"/api/v1/doctors/{doctor_id}/profile")

        assert profile_response.status_code == 200
        assert profile_response.json()["full_name"] == "Dr. Alice Smith"

    async def test_onboard_doctor_rejects_missing_required_field(
        self, authenticated_client: AsyncClient
    ) -> None:
        response = await authenticated_client.post("/api/v1/doctors", json={"employee_id": "EMP-1"})

        assert response.status_code == 422


class TestDoctorLicenses:
    async def test_add_and_list_licenses(
        self, authenticated_client: AsyncClient, test_user: User
    ) -> None:
        doctor_response = await authenticated_client.post(
            "/api/v1/doctors", json=_onboard_doctor_payload(test_user.id)
        )
        doctor_id = doctor_response.json()["id"]

        license_response = await authenticated_client.post(
            f"/api/v1/doctors/{doctor_id}/licenses",
            json={
                "license_number": f"LIC-{unique_suffix()}",
                "issuing_authority": "State Medical Board",
                "country": "USA",
                "issue_date": "2015-01-01",
                "expiry_date": "2030-01-01",
            },
        )
        assert license_response.status_code == 201
        assert license_response.json()["verification_status"] == "pending"

        list_response = await authenticated_client.get(f"/api/v1/doctors/{doctor_id}/licenses")
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1
