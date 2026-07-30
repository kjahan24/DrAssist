"""Unit tests for `AuditLogConsistencyService` — "Organization
consistency" for `actor_user_id`, including the no-op case when no actor
is given."""

from uuid import uuid4

import pytest

from app.modules.audit_log.application.services.audit_log_consistency_service import (
    AuditLogConsistencyService,
)
from app.modules.audit_log.domain.exceptions import (
    ActorNotFoundError,
    ActorOrganizationMismatchError,
)
from tests.unit.modules.audit_log.application.fakes import FakeUserQueryPort, make_user_summary


class TestValidateActorOrganization:
    async def test_none_actor_is_always_valid(self) -> None:
        service = AuditLogConsistencyService(user_query_port=FakeUserQueryPort())
        await service.validate_actor_organization(actor_user_id=None, organization_id=uuid4())

    async def test_matching_actor_passes(self) -> None:
        organization_id = uuid4()
        actor_user_id = uuid4()
        port = FakeUserQueryPort(
            existing_users={
                actor_user_id: make_user_summary(
                    user_id=actor_user_id, organization_id=organization_id
                )
            }
        )
        service = AuditLogConsistencyService(user_query_port=port)

        await service.validate_actor_organization(
            actor_user_id=actor_user_id, organization_id=organization_id
        )

    async def test_unknown_actor_raises(self) -> None:
        service = AuditLogConsistencyService(user_query_port=FakeUserQueryPort())
        with pytest.raises(ActorNotFoundError):
            await service.validate_actor_organization(
                actor_user_id=uuid4(), organization_id=uuid4()
            )

    async def test_mismatched_organization_raises(self) -> None:
        actor_user_id = uuid4()
        port = FakeUserQueryPort(
            existing_users={
                actor_user_id: make_user_summary(user_id=actor_user_id, organization_id=uuid4())
            }
        )
        service = AuditLogConsistencyService(user_query_port=port)

        with pytest.raises(ActorOrganizationMismatchError):
            await service.validate_actor_organization(
                actor_user_id=actor_user_id, organization_id=uuid4()
            )
