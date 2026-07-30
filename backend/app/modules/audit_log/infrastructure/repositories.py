"""Concrete SQLAlchemy repository implementation.

`add()` is insert-only — the opposite of every other module's own
"upsert" `add()` (look up by id, create if missing, otherwise overwrite):
here, a pre-existing row with the same id is a `AuditLogImmutableError`,
never an overwrite. This, together with `domain/repositories.py` never
declaring an `update()`/`delete()` method at all, is what "the repository
must reject update/delete operations" means concretely at this layer —
see `infrastructure/models.py` for the additional, defense-in-depth
database-trigger enforcement.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit_log.domain.entities import AuditLog
from app.modules.audit_log.domain.exceptions import AuditLogImmutableError
from app.modules.audit_log.domain.repositories import AuditLogRepository
from app.modules.audit_log.infrastructure.mappers import audit_log_to_domain, audit_log_to_model
from app.modules.audit_log.infrastructure.models import AuditLogModel


class SqlAlchemyAuditLogRepository(AuditLogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, audit_log_id: UUID) -> AuditLog | None:
        model = await self._session.get(AuditLogModel, audit_log_id)
        return audit_log_to_domain(model) if model is not None else None

    async def list_for_entity(self, *, entity_type: str, entity_id: UUID) -> list[AuditLog]:
        stmt = (
            select(AuditLogModel)
            .where(AuditLogModel.entity_type == entity_type, AuditLogModel.entity_id == entity_id)
            .order_by(AuditLogModel.created_at.desc())
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [audit_log_to_domain(model) for model in models]

    async def list_for_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[AuditLog]:
        stmt = (
            select(AuditLogModel)
            .where(AuditLogModel.organization_id == organization_id)
            .order_by(AuditLogModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [audit_log_to_domain(model) for model in models]

    async def list_for_actor(self, actor_user_id: UUID) -> list[AuditLog]:
        stmt = (
            select(AuditLogModel)
            .where(AuditLogModel.actor_user_id == actor_user_id)
            .order_by(AuditLogModel.created_at.desc())
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [audit_log_to_domain(model) for model in models]

    async def add(self, audit_log: AuditLog) -> None:
        existing = await self._session.get(AuditLogModel, audit_log.id)
        if existing is not None:
            raise AuditLogImmutableError(audit_log.id)
        self._session.add(audit_log_to_model(audit_log))
