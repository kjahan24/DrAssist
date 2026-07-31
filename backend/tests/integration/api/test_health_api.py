"""HTTP-level tests for the health endpoints — no auth required."""

import pytest
from httpx import AsyncClient

# See `tests.integration.api`'s own `__init__.py` docstring for why this
# must be declared directly in every test module in this package (not
# `__init__.py`, not a `conftest.py` hook).
pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestHealth:
    async def test_liveness_returns_ok(self, unauthenticated_client: AsyncClient) -> None:
        response = await unauthenticated_client.get("/api/v1/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    async def test_readiness_returns_ok_when_db_reachable(
        self, unauthenticated_client: AsyncClient
    ) -> None:
        response = await unauthenticated_client.get("/api/v1/health/db")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
