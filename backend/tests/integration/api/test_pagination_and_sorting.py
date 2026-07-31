"""Dedicated pagination/sorting tests against a representative list
endpoint (`GET /organizations/{id}/departments`) — offset/limit slicing,
default page size, sort_by/sort_order, and the invalid-sort-field 400.
See `app.api.pagination.paginate_and_sort` for the shared implementation
every list endpoint in this API uses."""

import pytest
from httpx import AsyncClient

from app.modules.organization.domain.entities import Organization

# See `tests.integration.api`'s own `__init__.py` docstring for why this
# must be declared directly in every test module in this package (not
# `__init__.py`, not a `conftest.py` hook).
pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _create_department(client: AsyncClient, organization_id: object, name: str) -> None:
    response = await client.post(
        f"/api/v1/organizations/{organization_id}/departments", json={"name": name}
    )
    assert response.status_code == 201


class TestPagination:
    async def test_limit_and_offset_slice_results(
        self, authenticated_client: AsyncClient, test_organization: Organization
    ) -> None:
        for name in ["Alpha", "Bravo", "Charlie", "Delta", "Echo"]:
            await _create_department(authenticated_client, test_organization.id, name)

        first_page = await authenticated_client.get(
            f"/api/v1/organizations/{test_organization.id}/departments",
            params={"limit": 2, "offset": 0},
        )
        assert first_page.status_code == 200
        first_body = first_page.json()
        assert first_body["total"] == 5
        assert first_body["limit"] == 2
        assert first_body["offset"] == 0
        assert len(first_body["items"]) == 2

        last_page = await authenticated_client.get(
            f"/api/v1/organizations/{test_organization.id}/departments",
            params={"limit": 2, "offset": 4},
        )
        assert last_page.status_code == 200
        assert len(last_page.json()["items"]) == 1

    async def test_default_pagination_applies_when_unspecified(
        self, authenticated_client: AsyncClient, test_organization: Organization
    ) -> None:
        await _create_department(authenticated_client, test_organization.id, "Solo")

        response = await authenticated_client.get(
            f"/api/v1/organizations/{test_organization.id}/departments"
        )

        assert response.status_code == 200
        body = response.json()
        assert body["offset"] == 0
        assert body["limit"] == 20

    async def test_limit_above_maximum_returns_422(
        self, authenticated_client: AsyncClient, test_organization: Organization
    ) -> None:
        response = await authenticated_client.get(
            f"/api/v1/organizations/{test_organization.id}/departments",
            params={"limit": 201},
        )

        assert response.status_code == 422

    async def test_negative_offset_returns_422(
        self, authenticated_client: AsyncClient, test_organization: Organization
    ) -> None:
        response = await authenticated_client.get(
            f"/api/v1/organizations/{test_organization.id}/departments",
            params={"offset": -1},
        )

        assert response.status_code == 422


class TestSorting:
    async def test_sort_by_name_ascending(
        self, authenticated_client: AsyncClient, test_organization: Organization
    ) -> None:
        for name in ["Charlie", "Alpha", "Bravo"]:
            await _create_department(authenticated_client, test_organization.id, name)

        response = await authenticated_client.get(
            f"/api/v1/organizations/{test_organization.id}/departments",
            params={"sort_by": "name", "sort_order": "asc"},
        )

        assert response.status_code == 200
        names = [item["name"] for item in response.json()["items"]]
        assert names == sorted(names)

    async def test_sort_by_name_descending(
        self, authenticated_client: AsyncClient, test_organization: Organization
    ) -> None:
        for name in ["Charlie", "Alpha", "Bravo"]:
            await _create_department(authenticated_client, test_organization.id, name)

        response = await authenticated_client.get(
            f"/api/v1/organizations/{test_organization.id}/departments",
            params={"sort_by": "name", "sort_order": "desc"},
        )

        assert response.status_code == 200
        names = [item["name"] for item in response.json()["items"]]
        assert names == sorted(names, reverse=True)

    async def test_unrecognized_sort_field_returns_400(
        self, authenticated_client: AsyncClient, test_organization: Organization
    ) -> None:
        await _create_department(authenticated_client, test_organization.id, "Solo")

        response = await authenticated_client.get(
            f"/api/v1/organizations/{test_organization.id}/departments",
            params={"sort_by": "not_a_real_field"},
        )

        assert response.status_code == 400
        assert response.json()["error_code"] == "bad_request"
