"""HTTP-level tests for the Patient module's router — create, get,
validation errors, cross-tenant isolation, and a sub-resource list."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.modules.organization.domain.entities import Organization
from tests.integration.api._helpers import unique_suffix

# See `tests.integration.api`'s own `__init__.py` docstring for why this
# must be declared directly in every test module in this package (not
# `__init__.py`, not a `conftest.py` hook).
pytestmark = pytest.mark.asyncio(loop_scope="session")


def _register_patient_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "patient_number": f"PAT-{unique_suffix()}",
        "first_name": "Jane",
        "last_name": "Doe",
        "gender": "female",
        "date_of_birth": "1990-01-01",
    }
    payload.update(overrides)
    return payload


class TestRegisterPatient:
    async def test_register_patient_returns_201(self, authenticated_client: AsyncClient) -> None:
        response = await authenticated_client.post(
            "/api/v1/patients", json=_register_patient_payload()
        )

        assert response.status_code == 201
        body = response.json()
        assert body["first_name"] == "Jane"
        assert body["gender"] == "female"
        assert body["status"] == "active"
        assert "id" in body

    async def test_register_patient_does_not_accept_organization_id(
        self, authenticated_client: AsyncClient, other_organization: Organization
    ) -> None:
        """`organization_id` was removed from `RegisterPatientRequest` —
        a client-supplied value here would otherwise let a caller
        register a patient into a different organization than their own
        (see `RegisterPatientRequest`'s own docstring). Sending it should
        simply be ignored, not accepted."""
        response = await authenticated_client.post(
            "/api/v1/patients",
            json=_register_patient_payload(organization_id=str(other_organization.id)),
        )

        assert response.status_code == 201
        get_response = await authenticated_client.get(f"/api/v1/patients/{response.json()['id']}")
        assert get_response.json()["organization_id"] != str(other_organization.id)

    async def test_register_patient_rejects_missing_required_field(
        self, authenticated_client: AsyncClient
    ) -> None:
        response = await authenticated_client.post("/api/v1/patients", json={"first_name": "Jane"})

        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "validation_error"
        assert "details" in body

    async def test_register_patient_rejects_invalid_gender(
        self, authenticated_client: AsyncClient
    ) -> None:
        response = await authenticated_client.post(
            "/api/v1/patients", json=_register_patient_payload(gender="not-a-gender")
        )

        assert response.status_code == 422

    async def test_register_patient_requires_authentication(
        self, unauthenticated_client: AsyncClient
    ) -> None:
        response = await unauthenticated_client.post(
            "/api/v1/patients", json=_register_patient_payload()
        )

        assert response.status_code == 401


class TestGetPatient:
    async def test_get_patient_returns_200(self, authenticated_client: AsyncClient) -> None:
        create_response = await authenticated_client.post(
            "/api/v1/patients", json=_register_patient_payload()
        )
        patient_id = create_response.json()["id"]

        response = await authenticated_client.get(f"/api/v1/patients/{patient_id}")

        assert response.status_code == 200
        assert response.json()["id"] == patient_id

    async def test_get_nonexistent_patient_returns_404(
        self, authenticated_client: AsyncClient
    ) -> None:
        response = await authenticated_client.get(f"/api/v1/patients/{uuid4()}")

        assert response.status_code == 404

    async def test_get_patient_from_other_organization_returns_404(
        self,
        authenticated_client: AsyncClient,
        authenticated_client_for_other_org: AsyncClient,
    ) -> None:
        create_response = await authenticated_client_for_other_org.post(
            "/api/v1/patients", json=_register_patient_payload()
        )
        patient_id = create_response.json()["id"]

        response = await authenticated_client.get(f"/api/v1/patients/{patient_id}")

        assert response.status_code == 404


class TestPatientAllergiesSubResource:
    async def test_record_and_list_allergies_paginated(
        self, authenticated_client: AsyncClient
    ) -> None:
        create_response = await authenticated_client.post(
            "/api/v1/patients", json=_register_patient_payload()
        )
        patient_id = create_response.json()["id"]

        allergy_response = await authenticated_client.post(
            f"/api/v1/patients/{patient_id}/allergies",
            json={
                "allergy_type": "drug",
                "allergen_name": "Penicillin",
                "severity": "severe",
            },
        )
        assert allergy_response.status_code == 201
        assert allergy_response.json()["allergen_name"] == "Penicillin"

        list_response = await authenticated_client.get(f"/api/v1/patients/{patient_id}/allergies")
        assert list_response.status_code == 200
        body = list_response.json()
        assert body["total"] == 1
        assert body["offset"] == 0
        assert body["limit"] == 20
        assert body["items"][0]["allergen_name"] == "Penicillin"
