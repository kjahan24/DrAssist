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

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.infrastructure.database.query_utils import (
    apply_date_range,
    apply_equality,
    apply_in_filter,
    apply_pagination,
    apply_partial_text_search,
    apply_sort,
    count_total,
    scope_to_organization,
)
from app.modules.audit_log.domain.entities import AuditLog
from app.modules.audit_log.domain.enums import AuditAction, AuditSource
from app.modules.audit_log.domain.exceptions import AuditLogImmutableError
from app.modules.audit_log.domain.repositories import AuditLogRepository
from app.modules.audit_log.infrastructure.mappers import audit_log_to_domain, audit_log_to_model
from app.modules.audit_log.infrastructure.models import AuditLogModel


class SqlAlchemyAuditLogRepository(AuditLogRepository):
    _SORT_COLUMNS: dict[str, InstrumentedAttribute[Any]] = {
        "created_at": AuditLogModel.created_at,
        "action": AuditLogModel.action,
        "source": AuditLogModel.source,
        "entity_type": AuditLogModel.entity_type,
    }

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

    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        actions: Sequence[AuditAction] | None = None,
        sources: Sequence[AuditSource] | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        actor_user_id: UUID | None = None,
        correlation_id: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[AuditLog], int]:
        stmt = select(AuditLogModel)
        stmt = scope_to_organization(stmt, AuditLogModel.organization_id, organization_id)
        stmt = apply_equality(stmt, AuditLogModel.entity_type, entity_type)
        stmt = apply_equality(stmt, AuditLogModel.entity_id, entity_id)
        stmt = apply_equality(stmt, AuditLogModel.actor_user_id, actor_user_id)
        stmt = apply_equality(stmt, AuditLogModel.correlation_id, correlation_id)
        stmt = apply_in_filter(stmt, AuditLogModel.action, actions)
        stmt = apply_in_filter(stmt, AuditLogModel.source, sources)
        stmt = apply_date_range(stmt, AuditLogModel.created_at, start=created_from, end=created_to)
        stmt = apply_partial_text_search(
            stmt,
            [AuditLogModel.entity_type, AuditLogModel.correlation_id, AuditLogModel.request_id],
            query,
        )

        total = await count_total(self._session, stmt)
        column = self._SORT_COLUMNS.get(sort_by, AuditLogModel.created_at)
        stmt = apply_sort(stmt, column, sort_order)
        stmt = apply_pagination(stmt, offset=offset, limit=limit)
        models = (await self._session.execute(stmt)).scalars().all()
        return [audit_log_to_domain(model) for model in models], total

    async def add(self, audit_log: AuditLog) -> None:
        existing = await self._session.get(AuditLogModel, audit_log.id)
        if existing is not None:
            raise AuditLogImmutableError(audit_log.id)
        self._session.add(audit_log_to_model(audit_log))
