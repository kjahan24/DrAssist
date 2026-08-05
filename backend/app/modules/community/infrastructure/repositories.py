"""Concrete SQLAlchemy repository implementations.

Every `add()` below is "upsert": look up the row by id, create it if
missing, then overwrite its mapped columns from the domain entity's
current in-memory state — see the identical pattern (and rationale) in
`app.modules.organization.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import func, select
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
from app.modules.community.domain.entities import Community, CommunityMember
from app.modules.community.domain.enums import (
    CommunityMemberStatus,
    CommunityRole,
    CommunityVisibility,
)
from app.modules.community.domain.repositories import CommunityMemberRepository, CommunityRepository
from app.modules.community.infrastructure.mappers import (
    apply_community_member_to_model,
    apply_community_to_model,
    community_member_to_domain,
    community_to_domain,
)
from app.modules.community.infrastructure.models import CommunityMemberModel, CommunityModel


class SqlAlchemyCommunityRepository(CommunityRepository):
    _SORT_COLUMNS: dict[str, InstrumentedAttribute[Any]] = {
        "created_at": CommunityModel.created_at,
        "updated_at": CommunityModel.updated_at,
        "name": CommunityModel.name,
        "slug": CommunityModel.slug,
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, community_id: UUID) -> Community | None:
        model = await self._session.get(CommunityModel, community_id)
        if model is None or model.deleted_at is not None:
            return None
        return community_to_domain(model)

    async def get_by_slug(self, organization_id: UUID, slug: str) -> Community | None:
        stmt = select(CommunityModel).where(
            CommunityModel.organization_id == organization_id,
            CommunityModel.slug == slug.strip().lower(),
            CommunityModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return community_to_domain(model) if model is not None else None

    async def list_by_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[Community]:
        stmt = (
            select(CommunityModel)
            .where(
                CommunityModel.organization_id == organization_id,
                CommunityModel.deleted_at.is_(None),
            )
            .order_by(CommunityModel.created_at)
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_to_domain(model) for model in models]

    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        visibilities: Sequence[CommunityVisibility] | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Community], int]:
        stmt = select(CommunityModel)
        stmt = scope_to_organization(stmt, CommunityModel.organization_id, organization_id)
        stmt = exclude_soft_deleted(
            stmt, CommunityModel.deleted_at, include_deleted=include_deleted
        )
        stmt = apply_in_filter(stmt, CommunityModel.visibility, visibilities)
        stmt = apply_date_range(stmt, CommunityModel.created_at, start=created_from, end=created_to)
        stmt = apply_date_range(stmt, CommunityModel.updated_at, start=updated_from, end=updated_to)
        stmt = apply_combined_text_search(
            stmt,
            full_text_columns=[CommunityModel.name, CommunityModel.description],
            partial_columns=[CommunityModel.name],
            term=query,
        )

        total = await count_total(self._session, stmt)
        column = self._SORT_COLUMNS.get(sort_by, CommunityModel.created_at)
        stmt = apply_sort(stmt, column, sort_order)
        stmt = apply_pagination(stmt, offset=offset, limit=limit)
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_to_domain(model) for model in models], total

    async def add(self, community: Community) -> None:
        model = await self._session.get(CommunityModel, community.id)
        if model is None:
            model = CommunityModel()
            self._session.add(model)
        apply_community_to_model(community, model)

    async def remove(self, community_id: UUID) -> None:
        model = await self._session.get(CommunityModel, community_id)
        if model is not None and model.deleted_at is None:
            model.deleted_at = datetime.now(UTC)


class SqlAlchemyCommunityMemberRepository(CommunityMemberRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, member_id: UUID) -> CommunityMember | None:
        model = await self._session.get(CommunityMemberModel, member_id)
        return community_member_to_domain(model) if model is not None else None

    async def get_by_community_and_user(
        self, community_id: UUID, user_id: UUID
    ) -> CommunityMember | None:
        stmt = select(CommunityMemberModel).where(
            CommunityMemberModel.community_id == community_id,
            CommunityMemberModel.user_id == user_id,
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return community_member_to_domain(model) if model is not None else None

    async def list_by_community(
        self, community_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[CommunityMember]:
        stmt = (
            select(CommunityMemberModel)
            .where(CommunityMemberModel.community_id == community_id)
            .order_by(CommunityMemberModel.joined_at)
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_member_to_domain(model) for model in models]

    async def list_by_user(
        self, user_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[CommunityMember]:
        stmt = (
            select(CommunityMemberModel)
            .where(CommunityMemberModel.user_id == user_id)
            .order_by(CommunityMemberModel.joined_at)
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_member_to_domain(model) for model in models]

    async def count_active_by_role(self, community_id: UUID, role: CommunityRole) -> int:
        stmt = select(func.count()).where(
            CommunityMemberModel.community_id == community_id,
            CommunityMemberModel.role == role,
            CommunityMemberModel.status == CommunityMemberStatus.ACTIVE,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def add(self, member: CommunityMember) -> None:
        model = await self._session.get(CommunityMemberModel, member.id)
        if model is None:
            model = CommunityMemberModel()
            self._session.add(model)
        apply_community_member_to_model(member, model)
