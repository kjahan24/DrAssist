"""HTTP-level tests for the Organization module's router.

`POST /organizations` is the one endpoint in the whole API that needs no
`CurrentUser` — it provisions a brand new tenant (see
`app.modules.organization.api.router`'s own module docstring) — so it is
exercised with `unauthenticated_client`; every other endpoint here reads
an *existing* organization and needs `authenticated_client`.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.modules.organization.domain.entities import Organization
from tests.integration.api._helpers import unique_suffix

# See `tests.integration.api`'s own `__init__.py` docstring for why this
# must be declared directly in every test module in this package (not
# `__init__.py`, not a `conftest.py` hook).
pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestCreateOrganization:
    async def test_create_organization_returns_201(
        self, unauthenticated_client: AsyncClient
    ) -> None:
        response = await unauthenticated_client.post(
            "/api/v1/organizations",
            json={
                "organization_code": f"ORG-{unique_suffix()}",
                "name": "New Test Clinic",
                "type": "clinic",
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "New Test Clinic"
        assert body["type"] == "clinic"
        assert body["is_active"] is True
        assert "id" in body

    async def test_create_organization_rejects_missing_required_field(
        self, unauthenticated_client: AsyncClient
    ) -> None:
        response = await unauthenticated_client.post(
            "/api/v1/organizations", json={"name": "Missing Code"}
        )

        assert response.status_code == 422

    async def test_create_organization_rejects_invalid_type(
        self, unauthenticated_client: AsyncClient
    ) -> None:
        response = await unauthenticated_client.post(
            "/api/v1/organizations",
            json={
                "organization_code": f"ORG-{unique_suffix()}",
                "name": "Bad Type Clinic",
                "type": "not-a-real-type",
            },
        )

        assert response.status_code == 422


class TestGetOrganization:
    async def test_get_organization_returns_200(
        self, authenticated_client: AsyncClient, test_organization: Organization
    ) -> None:
        response = await authenticated_client.get(f"/api/v1/organizations/{test_organization.id}")

        assert response.status_code == 200
        assert response.json()["id"] == str(test_organization.id)

    async def test_get_nonexistent_organization_returns_404(
        self, authenticated_client: AsyncClient
    ) -> None:
        response = await authenticated_client.get(f"/api/v1/organizations/{uuid4()}")

        assert response.status_code == 404

    async def test_get_other_organization_returns_404(
        self, authenticated_client: AsyncClient, other_organization: Organization
    ) -> None:
        """Cross-tenant reads 404, not the other org's data — see
        `ensure_same_organization`'s own docstring."""
        response = await authenticated_client.get(f"/api/v1/organizations/{other_organization.id}")

        assert response.status_code == 404


class TestOrganizationSettings:
    async def test_get_settings_returns_defaults(
        self, authenticated_client: AsyncClient, test_organization: Organization
    ) -> None:
        response = await authenticated_client.get(
            f"/api/v1/organizations/{test_organization.id}/settings"
        )

        assert response.status_code == 200
        body = response.json()
        assert body["organization_id"] == str(test_organization.id)
        assert body["appointment_duration_minutes"] == 30

    async def test_update_settings_persists_change(
        self, authenticated_client: AsyncClient, test_organization: Organization
    ) -> None:
        response = await authenticated_client.patch(
            f"/api/v1/organizations/{test_organization.id}/settings",
            json={"appointment_duration_minutes": 45},
        )

        assert response.status_code == 200
        assert response.json()["appointment_duration_minutes"] == 45


class TestDepartments:
    async def test_create_and_list_departments(
        self, authenticated_client: AsyncClient, test_organization: Organization
    ) -> None:
        create_response = await authenticated_client.post(
            f"/api/v1/organizations/{test_organization.id}/departments",
            json={"name": "Cardiology"},
        )
        assert create_response.status_code == 201
        assert create_response.json()["name"] == "Cardiology"
        assert create_response.json()["status"] == "active"

        list_response = await authenticated_client.get(
            f"/api/v1/organizations/{test_organization.id}/departments"
        )
        assert list_response.status_code == 200
        body = list_response.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Cardiology"
