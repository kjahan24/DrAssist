"""HTTP-level tests for the Notification module's router — new `api/`
package built by this task (see `container.py`'s own scope note); create
plus the mark-sent -> mark-delivered -> mark-read status chain."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organization.domain.entities import Organization
from tests.integration.api._helpers import persist_user

# See `tests.integration.api`'s own `__init__.py` docstring for why this
# must be declared directly in every test module in this package (not
# `__init__.py`, not a `conftest.py` hook).
pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestNotificationLifecycle:
    async def test_create_notification_returns_201_pending(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_organization: Organization,
    ) -> None:
        recipient = await persist_user(db_session, organization_id=test_organization.id)

        response = await authenticated_client.post(
            "/api/v1/notifications",
            json={
                "recipient_user_id": str(recipient.id),
                "notification_type": "general",
                "title": "Welcome",
                "message": "Your account is ready.",
                "priority": "normal",
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "pending"
        assert body["recipient_user_id"] == str(recipient.id)

    async def test_mark_sent_delivered_read_chain(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_organization: Organization,
    ) -> None:
        recipient = await persist_user(db_session, organization_id=test_organization.id)
        create_response = await authenticated_client.post(
            "/api/v1/notifications",
            json={
                "recipient_user_id": str(recipient.id),
                "notification_type": "general",
                "title": "Welcome",
                "message": "Your account is ready.",
                "priority": "normal",
            },
        )
        notification_id = create_response.json()["id"]

        sent = await authenticated_client.patch(
            f"/api/v1/notifications/{notification_id}/mark-sent"
        )
        assert sent.status_code == 200
        assert sent.json()["status"] == "sent"

        delivered = await authenticated_client.patch(
            f"/api/v1/notifications/{notification_id}/mark-delivered"
        )
        assert delivered.status_code == 200
        assert delivered.json()["status"] == "delivered"

        read = await authenticated_client.patch(
            f"/api/v1/notifications/{notification_id}/mark-read"
        )
        assert read.status_code == 200
        assert read.json()["status"] == "read"

    async def test_list_unread_for_recipient(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_organization: Organization,
    ) -> None:
        recipient = await persist_user(db_session, organization_id=test_organization.id)
        create_response = await authenticated_client.post(
            "/api/v1/notifications",
            json={
                "recipient_user_id": str(recipient.id),
                "notification_type": "general",
                "title": "Welcome",
                "message": "Your account is ready.",
                "priority": "normal",
            },
        )
        notification_id = create_response.json()["id"]
        await authenticated_client.patch(f"/api/v1/notifications/{notification_id}/mark-sent")
        await authenticated_client.patch(f"/api/v1/notifications/{notification_id}/mark-delivered")

        response = await authenticated_client.get(
            f"/api/v1/notifications/recipient/{recipient.id}/unread"
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["id"] == notification_id

    async def test_create_notification_rejects_invalid_priority(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_organization: Organization,
    ) -> None:
        recipient = await persist_user(db_session, organization_id=test_organization.id)

        response = await authenticated_client.post(
            "/api/v1/notifications",
            json={
                "recipient_user_id": str(recipient.id),
                "notification_type": "general",
                "title": "Welcome",
                "message": "Your account is ready.",
                "priority": "not-a-priority",
            },
        )

        assert response.status_code == 422
