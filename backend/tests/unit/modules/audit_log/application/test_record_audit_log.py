"""Unit tests for the `RecordAuditLog` use case, using in-memory fakes
for this module's own repository and the Authentication module's public
port (via `AuditLogConsistencyService`)."""

from uuid import uuid4

import pytest

from app.modules.audit_log.application.dto import RecordAuditLogInput
from app.modules.audit_log.application.services.audit_log_consistency_service import (
    AuditLogConsistencyService,
)
from app.modules.audit_log.application.use_cases.record_audit_log import RecordAuditLog
from app.modules.audit_log.domain.enums import AuditAction, AuditSource
from app.modules.audit_log.domain.exceptions import (
    ActorNotFoundError,
    ActorOrganizationMismatchError,
)
from tests.unit.modules.audit_log.application.fakes import (
    FakeAuditLogRepository,
    FakeUnitOfWork,
    FakeUserQueryPort,
    make_user_summary,
)


def _make_input(**overrides: object) -> RecordAuditLogInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "entity_type": "Appointment",
        "entity_id": uuid4(),
        "action": AuditAction.CREATE,
        "source": AuditSource.API,
    }
    defaults.update(overrides)
    return RecordAuditLogInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def audit_log_repository() -> FakeAuditLogRepository:
    return FakeAuditLogRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    audit_log_repository: FakeAuditLogRepository,
    unit_of_work: FakeUnitOfWork,
    user_query_port: FakeUserQueryPort,
) -> RecordAuditLog:
    return RecordAuditLog(
        audit_log_repository=audit_log_repository,
        consistency_service=AuditLogConsistencyService(user_query_port=user_query_port),
        unit_of_work=unit_of_work,
    )


class TestRecordAuditLog:
    async def test_records_an_audit_log_without_an_actor(
        self, audit_log_repository: FakeAuditLogRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        organization_id = uuid4()
        use_case = _use_case(audit_log_repository, unit_of_work, FakeUserQueryPort())

        output = await use_case.execute(
            _make_input(organization_id=organization_id, source=AuditSource.SYSTEM)
        )

        stored = await audit_log_repository.get_by_id(output.audit_log_id)
        assert stored is not None
        assert stored.organization_id == organization_id
        assert stored.actor_user_id is None
        assert unit_of_work.committed is True

    async def test_records_an_audit_log_with_a_matching_actor(
        self, audit_log_repository: FakeAuditLogRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        organization_id = uuid4()
        actor_user_id = uuid4()
        user_port = FakeUserQueryPort(
            existing_users={
                actor_user_id: make_user_summary(
                    user_id=actor_user_id, organization_id=organization_id
                )
            }
        )
        use_case = _use_case(audit_log_repository, unit_of_work, user_port)

        output = await use_case.execute(
            _make_input(organization_id=organization_id, actor_user_id=actor_user_id)
        )

        stored = await audit_log_repository.get_by_id(output.audit_log_id)
        assert stored is not None
        assert stored.actor_user_id == actor_user_id

    async def test_unknown_actor_raises(
        self, audit_log_repository: FakeAuditLogRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(audit_log_repository, unit_of_work, FakeUserQueryPort())
        with pytest.raises(ActorNotFoundError):
            await use_case.execute(_make_input(actor_user_id=uuid4()))

    async def test_actor_from_a_different_organization_raises(
        self, audit_log_repository: FakeAuditLogRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        actor_user_id = uuid4()
        user_port = FakeUserQueryPort(
            existing_users={
                actor_user_id: make_user_summary(user_id=actor_user_id, organization_id=uuid4())
            }
        )
        use_case = _use_case(audit_log_repository, unit_of_work, user_port)

        with pytest.raises(ActorOrganizationMismatchError):
            await use_case.execute(
                _make_input(organization_id=uuid4(), actor_user_id=actor_user_id)
            )

    async def test_old_and_new_values_are_persisted(
        self, audit_log_repository: FakeAuditLogRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(audit_log_repository, unit_of_work, FakeUserQueryPort())

        output = await use_case.execute(
            _make_input(
                action=AuditAction.UPDATE,
                old_values={"status": "scheduled"},
                new_values={"status": "confirmed"},
            )
        )

        stored = await audit_log_repository.get_by_id(output.audit_log_id)
        assert stored is not None
        assert stored.old_values == {"status": "scheduled"}
        assert stored.new_values == {"status": "confirmed"}
