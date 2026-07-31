"""Integration tests for `SqlAlchemyAuditLogRepository`, including the
FKs to `organizations`/`users`, the app-layer insert-only guard, and the
database-trigger-enforced immutability (`reject_mutation()` /
`trg_audit_logs_immutable`), against a real PostgreSQL instance.
"""

from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.audit_log._helpers import (
    persist_organization,
    persist_organization_and_user,
)

from app.modules.audit_log.domain.entities import AuditLog
from app.modules.audit_log.domain.enums import AuditAction, AuditSource
from app.modules.audit_log.domain.exceptions import AuditLogImmutableError
from app.modules.audit_log.infrastructure.models import AuditLogModel
from app.modules.audit_log.infrastructure.repositories import SqlAlchemyAuditLogRepository


class TestAuditLogRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, user = await persist_organization_and_user(db_session)
        repo = SqlAlchemyAuditLogRepository(db_session)
        entity_id = uuid4()

        audit_log = AuditLog.record(
            organization_id=organization.id,
            actor_user_id=user.id,
            entity_type="Appointment",
            entity_id=entity_id,
            action=AuditAction.UPDATE,
            source=AuditSource.API,
            old_values={"status": "scheduled"},
            new_values={"status": "confirmed"},
            ip_address="203.0.113.5",
            user_agent="Mozilla/5.0",
            request_id="req-123",
            correlation_id="corr-456",
        )
        await repo.add(audit_log)
        await db_session.commit()

        reloaded = await repo.get_by_id(audit_log.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.actor_user_id == user.id
        assert reloaded.entity_type == "Appointment"
        assert reloaded.entity_id == entity_id
        assert reloaded.action is AuditAction.UPDATE
        assert reloaded.source is AuditSource.API
        assert reloaded.old_values == {"status": "scheduled"}
        assert reloaded.new_values == {"status": "confirmed"}
        assert reloaded.ip_address == "203.0.113.5"
        assert reloaded.user_agent == "Mozilla/5.0"
        assert reloaded.request_id == "req-123"
        assert reloaded.correlation_id == "corr-456"
        assert reloaded.created_at is not None

    async def test_save_without_an_actor_preserves_null(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyAuditLogRepository(db_session)

        audit_log = AuditLog.record(
            organization_id=organization.id,
            entity_type="Organization",
            entity_id=organization.id,
            action=AuditAction.CREATE,
            source=AuditSource.SYSTEM,
        )
        await repo.add(audit_log)
        await db_session.commit()

        reloaded = await repo.get_by_id(audit_log.id)
        assert reloaded is not None
        assert reloaded.actor_user_id is None
        assert reloaded.old_values is None
        assert reloaded.new_values is None


class TestListQueries:
    async def test_list_for_entity_returns_only_that_entitys_audit_logs(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyAuditLogRepository(db_session)
        entity_id = uuid4()

        mine = AuditLog.record(
            organization_id=organization.id,
            entity_type="Appointment",
            entity_id=entity_id,
            action=AuditAction.CREATE,
            source=AuditSource.API,
        )
        other = AuditLog.record(
            organization_id=organization.id,
            entity_type="Appointment",
            entity_id=uuid4(),
            action=AuditAction.CREATE,
            source=AuditSource.API,
        )
        await repo.add(mine)
        await repo.add(other)
        await db_session.commit()

        results = await repo.list_for_entity(entity_type="Appointment", entity_id=entity_id)
        assert [a.id for a in results] == [mine.id]

    async def test_list_for_organization_respects_offset_and_limit(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyAuditLogRepository(db_session)

        for _ in range(3):
            await repo.add(
                AuditLog.record(
                    organization_id=organization.id,
                    entity_type="Appointment",
                    entity_id=uuid4(),
                    action=AuditAction.CREATE,
                    source=AuditSource.API,
                )
            )
        await db_session.commit()

        page = await repo.list_for_organization(organization.id, offset=0, limit=2)
        assert len(page) == 2

    async def test_list_for_actor_returns_only_that_actors_audit_logs(
        self, db_session: AsyncSession
    ) -> None:
        organization, user = await persist_organization_and_user(db_session)
        repo = SqlAlchemyAuditLogRepository(db_session)

        mine = AuditLog.record(
            organization_id=organization.id,
            actor_user_id=user.id,
            entity_type="Appointment",
            entity_id=uuid4(),
            action=AuditAction.LOGIN,
            source=AuditSource.API,
        )
        system_generated = AuditLog.record(
            organization_id=organization.id,
            entity_type="Appointment",
            entity_id=uuid4(),
            action=AuditAction.CREATE,
            source=AuditSource.SYSTEM,
        )
        await repo.add(mine)
        await repo.add(system_generated)
        await db_session.commit()

        results = await repo.list_for_actor(user.id)
        assert [a.id for a in results] == [mine.id]


class TestAuditLogSearch:
    """Search & Filtering module — `SqlAlchemyAuditLogRepository.search`."""

    async def test_scopes_to_organization_at_the_sql_layer(self, db_session: AsyncSession) -> None:
        organization, user = await persist_organization_and_user(db_session)
        other_org, other_user = await persist_organization_and_user(db_session)
        repo = SqlAlchemyAuditLogRepository(db_session)
        entry = AuditLog.record(
            organization_id=organization.id,
            actor_user_id=user.id,
            entity_type="Appointment",
            entity_id=uuid4(),
            action=AuditAction.CREATE,
            source=AuditSource.API,
        )
        other = AuditLog.record(
            organization_id=other_org.id,
            actor_user_id=other_user.id,
            entity_type="Appointment",
            entity_id=uuid4(),
            action=AuditAction.CREATE,
            source=AuditSource.API,
        )
        await repo.add(entry)
        await repo.add(other)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id)

        assert total == 1
        assert [a.id for a in results] == [entry.id]

    async def test_action_source_and_actor_filters(self, db_session: AsyncSession) -> None:
        organization, user = await persist_organization_and_user(db_session)
        repo = SqlAlchemyAuditLogRepository(db_session)
        login = AuditLog.record(
            organization_id=organization.id,
            actor_user_id=user.id,
            entity_type="Session",
            entity_id=uuid4(),
            action=AuditAction.LOGIN,
            source=AuditSource.API,
        )
        system_create = AuditLog.record(
            organization_id=organization.id,
            entity_type="Appointment",
            entity_id=uuid4(),
            action=AuditAction.CREATE,
            source=AuditSource.SYSTEM,
        )
        await repo.add(login)
        await repo.add(system_create)
        await db_session.commit()

        results, total = await repo.search(
            organization_id=organization.id,
            actions=[AuditAction.LOGIN],
            sources=[AuditSource.API],
            actor_user_id=user.id,
        )

        assert total == 1
        assert [a.id for a in results] == [login.id]

    async def test_query_matches_entity_type_and_correlation_id_partially(
        self, db_session: AsyncSession
    ) -> None:
        organization, user = await persist_organization_and_user(db_session)
        repo = SqlAlchemyAuditLogRepository(db_session)
        entry = AuditLog.record(
            organization_id=organization.id,
            actor_user_id=user.id,
            entity_type="LabOrder",
            entity_id=uuid4(),
            action=AuditAction.CREATE,
            source=AuditSource.API,
            correlation_id="corr-unique-042",
        )
        await repo.add(entry)
        await db_session.commit()

        by_entity_type, entity_total = await repo.search(
            organization_id=organization.id, query="LabOrder"
        )
        by_correlation, correlation_total = await repo.search(
            organization_id=organization.id, query="unique-042"
        )

        assert entity_total == 1
        assert [a.id for a in by_entity_type] == [entry.id]
        assert correlation_total == 1
        assert [a.id for a in by_correlation] == [entry.id]

    async def test_default_sort_order_is_newest_first(self, db_session: AsyncSession) -> None:
        organization, user = await persist_organization_and_user(db_session)
        repo = SqlAlchemyAuditLogRepository(db_session)
        first = AuditLog.record(
            organization_id=organization.id,
            actor_user_id=user.id,
            entity_type="Appointment",
            entity_id=uuid4(),
            action=AuditAction.CREATE,
            source=AuditSource.API,
        )
        await repo.add(first)
        await db_session.commit()
        second = AuditLog.record(
            organization_id=organization.id,
            actor_user_id=user.id,
            entity_type="Appointment",
            entity_id=uuid4(),
            action=AuditAction.UPDATE,
            source=AuditSource.API,
        )
        await repo.add(second)
        await db_session.commit()

        results, _total = await repo.search(organization_id=organization.id)

        assert [a.id for a in results] == [second.id, first.id]


class TestAuditLogRequiresValidReferences:
    async def test_nonexistent_organization_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyAuditLogRepository(db_session)

        audit_log = AuditLog.record(
            organization_id=uuid4(),
            entity_type="Appointment",
            entity_id=uuid4(),
            action=AuditAction.CREATE,
            source=AuditSource.API,
        )
        await repo.add(audit_log)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_actor_user_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyAuditLogRepository(db_session)

        audit_log = AuditLog.record(
            organization_id=organization.id,
            actor_user_id=uuid4(),
            entity_type="Appointment",
            entity_id=uuid4(),
            action=AuditAction.CREATE,
            source=AuditSource.API,
        )
        await repo.add(audit_log)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestInsertOnlyGuard:
    """`AuditLogRepository.add()` is insert-only — see its own docstring.
    This targets the application-layer guard specifically (raised before
    any SQL is issued for the second call), distinct from
    `TestDatabaseTriggerImmutability` below, which targets the
    database-level guard."""

    async def test_adding_the_same_id_twice_raises(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyAuditLogRepository(db_session)

        audit_log = AuditLog.record(
            organization_id=organization.id,
            entity_type="Appointment",
            entity_id=uuid4(),
            action=AuditAction.CREATE,
            source=AuditSource.API,
        )
        await repo.add(audit_log)
        await db_session.commit()

        with pytest.raises(AuditLogImmutableError):
            await repo.add(audit_log)


class TestDatabaseTriggerImmutability:
    """`Notification`/`Appointment`-style `__post_init__`/application-layer
    validation has no equivalent here for mutation, because there is no
    mutation method at all (see `domain/entities.py`) — the only way to
    even attempt an `UPDATE`/`DELETE` is to bypass the domain and
    application layers entirely, the way a direct SQL edit (or a
    compromised application role) would. This test does exactly that,
    against the real `trg_audit_logs_immutable` trigger, the same
    "prove the defense-in-depth layer actually works" pattern
    `tests.integration.modules.appointment.test_appointment_repository
    .TestCheckConstraints` already established for `CHECK` constraints.
    """

    async def test_direct_update_is_rejected_by_trigger(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyAuditLogRepository(db_session)
        audit_log = AuditLog.record(
            organization_id=organization.id,
            entity_type="Appointment",
            entity_id=uuid4(),
            action=AuditAction.CREATE,
            source=AuditSource.API,
        )
        await repo.add(audit_log)
        await db_session.commit()

        with pytest.raises(DBAPIError):
            await db_session.execute(
                sa.update(AuditLogModel)
                .where(AuditLogModel.id == audit_log.id)
                .values(entity_type="Tampered")
            )
        await db_session.rollback()

        reloaded = await repo.get_by_id(audit_log.id)
        assert reloaded is not None
        assert reloaded.entity_type == "Appointment"

    async def test_direct_delete_is_rejected_by_trigger(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyAuditLogRepository(db_session)
        audit_log = AuditLog.record(
            organization_id=organization.id,
            entity_type="Appointment",
            entity_id=uuid4(),
            action=AuditAction.CREATE,
            source=AuditSource.API,
        )
        await repo.add(audit_log)
        await db_session.commit()

        with pytest.raises(DBAPIError):
            await db_session.execute(
                sa.delete(AuditLogModel).where(AuditLogModel.id == audit_log.id)
            )
        await db_session.rollback()

        assert await repo.get_by_id(audit_log.id) is not None
