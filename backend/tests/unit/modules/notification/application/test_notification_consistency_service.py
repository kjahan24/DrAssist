"""Unit tests for `NotificationConsistencyService` — "Organization
consistency" (derivation) and "recipient existence" for
`recipient_user_id`."""

from uuid import uuid4

import pytest

from app.modules.notification.application.services.notification_consistency_service import (
    NotificationConsistencyService,
)
from app.modules.notification.domain.exceptions import RecipientNotFoundError
from tests.unit.modules.notification.application.fakes import FakeUserQueryPort, make_user_summary


class TestResolveOrganizationForRecipient:
    async def test_returns_the_recipients_own_organization_id(self) -> None:
        organization_id = uuid4()
        recipient_user_id = uuid4()
        port = FakeUserQueryPort(
            existing_users={
                recipient_user_id: make_user_summary(
                    user_id=recipient_user_id, organization_id=organization_id
                )
            }
        )
        service = NotificationConsistencyService(user_query_port=port)

        result = await service.resolve_organization_for_recipient(recipient_user_id)

        assert result == organization_id

    async def test_unknown_recipient_raises(self) -> None:
        service = NotificationConsistencyService(user_query_port=FakeUserQueryPort())
        with pytest.raises(RecipientNotFoundError):
            await service.resolve_organization_for_recipient(uuid4())
