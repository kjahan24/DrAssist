"""Cross-cutting error-handling tests: every `AppError`/`DomainError`
resolves to the same `{"error_code", "message"}` JSON shape (plus
`"details"` for validation errors) — see
`app.middlewares.error_handler.register_exception_handlers`."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.integration.api._helpers import unique_suffix

# See `tests.integration.api`'s own `__init__.py` docstring for why this
# must be declared directly in every test module in this package (not
# `__init__.py`, not a `conftest.py` hook).
pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestUnauthorized:
    async def test_missing_bearer_token_returns_401(
        self, unauthenticated_client: AsyncClient
    ) -> None:
        response = await unauthenticated_client.get(f"/api/v1/patients/{uuid4()}")

        assert response.status_code == 401
        assert response.json()["error_code"] == "unauthorized"


class TestNotFound:
    async def test_unknown_resource_returns_404_with_error_shape(
        self, authenticated_client: AsyncClient
    ) -> None:
        response = await authenticated_client.get(f"/api/v1/patients/{uuid4()}")

        assert response.status_code == 404
        body = response.json()
        assert body["error_code"] == "not_found"
        assert "message" in body


class TestValidation:
    async def test_malformed_uuid_path_param_returns_422(
        self, authenticated_client: AsyncClient
    ) -> None:
        response = await authenticated_client.get("/api/v1/patients/not-a-uuid")

        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "validation_error"
        assert isinstance(body["details"], list)

    async def test_missing_required_body_field_returns_422(
        self, authenticated_client: AsyncClient
    ) -> None:
        response = await authenticated_client.post("/api/v1/patients", json={})

        assert response.status_code == 422


class TestConflict:
    async def test_duplicate_organization_code_returns_409(
        self, unauthenticated_client: AsyncClient
    ) -> None:
        code = f"ORG-{unique_suffix()}"
        payload = {"organization_code": code, "name": "First Org", "type": "clinic"}

        first = await unauthenticated_client.post("/api/v1/organizations", json=payload)
        assert first.status_code == 201

        second = await unauthenticated_client.post(
            "/api/v1/organizations",
            json={**payload, "name": "Second Org With Same Code"},
        )

        assert second.status_code == 409
        assert second.json()["error_code"] == "conflict"
