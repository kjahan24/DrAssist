"""HTTP-level tests for the Audit Log module's router — new `api/`
package built by this task (see `container.py`'s own scope note).
Read-only: there is no `POST` endpoint (see `api/schemas.py`'s own
docstring), so every test seeds its row via `RecordAuditLog` directly,
through the `record_audit_log` test helper."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organization.domain.entities import Organization
from tests.integration.api._helpers import record_audit_log

# See `tests.integration.api`'s own `__init__.py` docstring for why this
# must be declared directly in every test module in this package (not
# `__init__.py`, not a `conftest.py` hook).
pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestGetAuditLog:
    async def test_get_audit_log_returns_200(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_organization: Organization,
    ) -> None:
        entity_id = uuid4()
        audit_log_id = await record_audit_log(
            db_session, organization_id=test_organization.id, entity_id=entity_id
        )

        response = await authenticated_client.get(f"/api/v1/audit-logs/{audit_log_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["entity_id"] == str(entity_id)
        assert body["action"] == "create"
        assert body["source"] == "api"

    async def test_get_nonexistent_audit_log_returns_404(
        self, authenticated_client: AsyncClient
    ) -> None:
        response = await authenticated_client.get(f"/api/v1/audit-logs/{uuid4()}")

        assert response.status_code == 404

    async def test_get_audit_log_from_other_organization_returns_404(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        other_organization: Organization,
    ) -> None:
        audit_log_id = await record_audit_log(db_session, organization_id=other_organization.id)

        response = await authenticated_client.get(f"/api/v1/audit-logs/{audit_log_id}")

        assert response.status_code == 404


class TestListAuditLogs:
    async def test_list_for_organization_only_returns_own_org(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_organization: Organization,
        other_organization: Organization,
    ) -> None:
        own_id = await record_audit_log(db_session, organization_id=test_organization.id)
        await record_audit_log(db_session, organization_id=other_organization.id)

        response = await authenticated_client.get("/api/v1/audit-logs")

        assert response.status_code == 200
        body = response.json()
        returned_ids = {item["id"] for item in body["items"]}
        assert str(own_id) in returned_ids
        assert all(item["organization_id"] == str(test_organization.id) for item in body["items"])

    async def test_list_for_entity_filters_by_entity(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_organization: Organization,
    ) -> None:
        entity_id = uuid4()
        await record_audit_log(
            db_session,
            organization_id=test_organization.id,
            entity_type="patient",
            entity_id=entity_id,
        )
        await record_audit_log(
            db_session, organization_id=test_organization.id, entity_type="patient"
        )

        response = await authenticated_client.get(f"/api/v1/audit-logs/entity/patient/{entity_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["entity_id"] == str(entity_id)

    async def test_list_for_entity_excludes_other_organizations(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_organization: Organization,
        other_organization: Organization,
    ) -> None:
        """Defense-in-depth tenant filter — `list_for_entity` has no
        `organization_id` parameter at the query-service level, so the
        router filters the result set itself (see this module's
        `api/router.py` own docstring)."""
        entity_id = uuid4()
        await record_audit_log(
            db_session,
            organization_id=other_organization.id,
            entity_type="patient",
            entity_id=entity_id,
        )

        response = await authenticated_client.get(f"/api/v1/audit-logs/entity/patient/{entity_id}")

        assert response.status_code == 200
        assert response.json()["total"] == 0
