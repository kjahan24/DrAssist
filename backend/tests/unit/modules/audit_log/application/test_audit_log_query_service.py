"""Unit tests for `AuditLogQueryService`."""

from uuid import uuid4

from app.modules.audit_log.application.services.audit_log_query_service import (
    AuditLogQueryService,
)
from app.modules.audit_log.domain.entities import AuditLog
from app.modules.audit_log.domain.enums import AuditAction, AuditSource
from tests.unit.modules.audit_log.application.fakes import FakeAuditLogRepository


def _make_audit_log(**overrides: object) -> AuditLog:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "entity_type": "Appointment",
        "entity_id": uuid4(),
        "action": AuditAction.CREATE,
        "source": AuditSource.API,
    }
    defaults.update(overrides)
    return AuditLog.record(**defaults)  # type: ignore[arg-type]


class TestGetById:
    async def test_returns_a_summary_for_a_stored_audit_log(self) -> None:
        repo = FakeAuditLogRepository()
        audit_log = _make_audit_log()
        await repo.add(audit_log)
        service = AuditLogQueryService(audit_log_repository=repo)

        summary = await service.get_by_id(audit_log.id)

        assert summary is not None
        assert summary.audit_log_id == audit_log.id
        assert summary.entity_type == "Appointment"

    async def test_returns_none_for_an_unknown_audit_log(self) -> None:
        service = AuditLogQueryService(audit_log_repository=FakeAuditLogRepository())
        assert await service.get_by_id(uuid4()) is None


class TestListForEntity:
    async def test_returns_only_that_entitys_audit_logs(self) -> None:
        repo = FakeAuditLogRepository()
        entity_id = uuid4()
        mine = _make_audit_log(entity_type="Appointment", entity_id=entity_id)
        other = _make_audit_log(entity_type="Appointment", entity_id=uuid4())
        different_type = _make_audit_log(entity_type="Patient", entity_id=entity_id)
        await repo.add(mine)
        await repo.add(other)
        await repo.add(different_type)
        service = AuditLogQueryService(audit_log_repository=repo)

        results = await service.list_for_entity(entity_type="Appointment", entity_id=entity_id)

        assert [r.audit_log_id for r in results] == [mine.id]


class TestListForOrganization:
    async def test_returns_only_that_organizations_audit_logs(self) -> None:
        repo = FakeAuditLogRepository()
        organization_id = uuid4()
        mine = _make_audit_log(organization_id=organization_id)
        other = _make_audit_log(organization_id=uuid4())
        await repo.add(mine)
        await repo.add(other)
        service = AuditLogQueryService(audit_log_repository=repo)

        results = await service.list_for_organization(organization_id)

        assert [r.audit_log_id for r in results] == [mine.id]

    async def test_returns_empty_list_for_an_organization_without_audit_logs(self) -> None:
        service = AuditLogQueryService(audit_log_repository=FakeAuditLogRepository())
        assert await service.list_for_organization(uuid4()) == []


class TestListForActor:
    async def test_returns_only_that_actors_audit_logs(self) -> None:
        repo = FakeAuditLogRepository()
        actor_user_id = uuid4()
        mine = _make_audit_log(actor_user_id=actor_user_id)
        system_generated = _make_audit_log(actor_user_id=None)
        await repo.add(mine)
        await repo.add(system_generated)
        service = AuditLogQueryService(audit_log_repository=repo)

        results = await service.list_for_actor(actor_user_id)

        assert [r.audit_log_id for r in results] == [mine.id]
