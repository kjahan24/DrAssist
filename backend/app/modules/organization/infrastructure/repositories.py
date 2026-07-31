"""Concrete SQLAlchemy repository implementations.

Every `add()` below is "upsert": look up the row by id, create it if
missing, then overwrite its mapped columns from the domain entity's
current in-memory state — see the identical pattern (and rationale) in
`app.modules.authentication.infrastructure.repositories`.

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
    apply_combined_text_search,
    apply_date_range,
    apply_in_filter,
    apply_pagination,
    apply_sort,
    count_total,
    exclude_soft_deleted,
    scope_to_organization,
)
from app.modules.organization.domain.entities import Department, Organization, OrganizationSettings
from app.modules.organization.domain.enums import DepartmentStatus
from app.modules.organization.domain.repositories import (
    DepartmentRepository,
    OrganizationRepository,
    OrganizationSettingsRepository,
)
from app.modules.organization.infrastructure.mappers import (
    apply_department_to_model,
    apply_organization_settings_to_model,
    apply_organization_to_model,
    department_to_domain,
    organization_settings_to_domain,
    organization_to_domain,
)
from app.modules.organization.infrastructure.models import (
    DepartmentModel,
    OrganizationModel,
    OrganizationSettingsModel,
)


class SqlAlchemyOrganizationRepository(OrganizationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        model = await self._session.get(OrganizationModel, organization_id)
        if model is None or model.deleted_at is not None:
            return None
        return organization_to_domain(model)

    async def get_by_code(self, organization_code: str) -> Organization | None:
        stmt = select(OrganizationModel).where(
            OrganizationModel.organization_code == organization_code.strip().upper(),
            OrganizationModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return organization_to_domain(model) if model is not None else None

    async def list_active(self, *, offset: int = 0, limit: int = 20) -> list[Organization]:
        stmt = (
            select(OrganizationModel)
            .where(OrganizationModel.is_active.is_(True), OrganizationModel.deleted_at.is_(None))
            .order_by(OrganizationModel.created_at)
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [organization_to_domain(model) for model in models]

    async def add(self, organization: Organization) -> None:
        model = await self._session.get(OrganizationModel, organization.id)
        if model is None:
            model = OrganizationModel()
            self._session.add(model)
        apply_organization_to_model(organization, model)


class SqlAlchemyOrganizationSettingsRepository(OrganizationSettingsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_organization_id(self, organization_id: UUID) -> OrganizationSettings | None:
        stmt = select(OrganizationSettingsModel).where(
            OrganizationSettingsModel.organization_id == organization_id,
            OrganizationSettingsModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return organization_settings_to_domain(model) if model is not None else None

    async def add(self, settings: OrganizationSettings) -> None:
        model = await self._session.get(OrganizationSettingsModel, settings.id)
        if model is None:
            model = OrganizationSettingsModel()
            self._session.add(model)
        apply_organization_settings_to_model(settings, model)


class SqlAlchemyDepartmentRepository(DepartmentRepository):
    _SORT_COLUMNS: dict[str, InstrumentedAttribute[Any]] = {
        "created_at": DepartmentModel.created_at,
        "updated_at": DepartmentModel.updated_at,
        "name": DepartmentModel.name,
        "status": DepartmentModel.status,
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, department_id: UUID) -> Department | None:
        model = await self._session.get(DepartmentModel, department_id)
        if model is None or model.deleted_at is not None:
            return None
        return department_to_domain(model)

    async def list_by_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[Department]:
        stmt = (
            select(DepartmentModel)
            .where(
                DepartmentModel.organization_id == organization_id,
                DepartmentModel.deleted_at.is_(None),
            )
            .order_by(DepartmentModel.created_at)
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [department_to_domain(model) for model in models]

    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[DepartmentStatus] | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Department], int]:
        stmt = select(DepartmentModel)
        stmt = scope_to_organization(stmt, DepartmentModel.organization_id, organization_id)
        stmt = exclude_soft_deleted(
            stmt, DepartmentModel.deleted_at, include_deleted=include_deleted
        )
        stmt = apply_in_filter(stmt, DepartmentModel.status, statuses)
        stmt = apply_date_range(
            stmt, DepartmentModel.created_at, start=created_from, end=created_to
        )
        stmt = apply_date_range(
            stmt, DepartmentModel.updated_at, start=updated_from, end=updated_to
        )
        stmt = apply_combined_text_search(
            stmt,
            full_text_columns=[DepartmentModel.name, DepartmentModel.description],
            partial_columns=[DepartmentModel.name],
            term=query,
        )

        total = await count_total(self._session, stmt)
        column = self._SORT_COLUMNS.get(sort_by, DepartmentModel.created_at)
        stmt = apply_sort(stmt, column, sort_order)
        stmt = apply_pagination(stmt, offset=offset, limit=limit)
        models = (await self._session.execute(stmt)).scalars().all()
        return [department_to_domain(model) for model in models], total

    async def add(self, department: Department) -> None:
        model = await self._session.get(DepartmentModel, department.id)
        if model is None:
            model = DepartmentModel()
            self._session.add(model)
        apply_department_to_model(department, model)
