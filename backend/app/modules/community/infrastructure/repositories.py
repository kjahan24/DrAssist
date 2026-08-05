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
    apply_equality,
    apply_in_filter,
    apply_pagination,
    apply_partial_text_search,
    apply_sort,
    count_total,
    exclude_soft_deleted,
    scope_to_organization,
)
from app.modules.community.domain.entities import (
    Community,
    CommunityCategory,
    CommunityMember,
    CommunityRule,
    CommunityTag,
)
from app.modules.community.domain.enums import (
    CommunityMemberStatus,
    CommunityRole,
    CommunityVisibility,
)
from app.modules.community.domain.repositories import (
    CommunityCategoryRepository,
    CommunityMemberRepository,
    CommunityRepository,
    CommunityRuleRepository,
    CommunityTagRepository,
)
from app.modules.community.infrastructure.mappers import (
    apply_community_category_to_model,
    apply_community_member_to_model,
    apply_community_rule_to_model,
    apply_community_tag_to_model,
    apply_community_to_model,
    community_category_to_domain,
    community_member_to_domain,
    community_rule_to_domain,
    community_tag_to_domain,
    community_to_domain,
)
from app.modules.community.infrastructure.models import (
    CommunityCategoryModel,
    CommunityMemberModel,
    CommunityModel,
    CommunityRuleModel,
    CommunityTagAssignmentModel,
    CommunityTagModel,
)


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
        category_id: UUID | None = None,
        tag_ids: Sequence[UUID] | None = None,
        featured_only: bool = False,
        verified_only: bool = False,
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
        stmt = apply_equality(stmt, CommunityModel.category_id, category_id)
        if featured_only:
            stmt = stmt.where(CommunityModel.is_featured.is_(True))
        if verified_only:
            stmt = stmt.where(CommunityModel.is_verified.is_(True))
        if tag_ids:
            tagged_community_ids = select(CommunityTagAssignmentModel.community_id).where(
                CommunityTagAssignmentModel.tag_id.in_(tag_ids)
            )
            stmt = stmt.where(CommunityModel.id.in_(tagged_community_ids))
        stmt = apply_date_range(stmt, CommunityModel.created_at, start=created_from, end=created_to)
        stmt = apply_date_range(stmt, CommunityModel.updated_at, start=updated_from, end=updated_to)
        stmt = apply_combined_text_search(
            stmt,
            full_text_columns=[CommunityModel.name, CommunityModel.description],
            partial_columns=[CommunityModel.name],
            term=query,
        )

        total = await count_total(self._session, stmt)

        if sort_by == "member_count":
            active_member_counts = (
                select(
                    CommunityMemberModel.community_id.label("community_id"),
                    func.count(CommunityMemberModel.id).label("member_count"),
                )
                .where(CommunityMemberModel.status == CommunityMemberStatus.ACTIVE)
                .group_by(CommunityMemberModel.community_id)
                .subquery()
            )
            member_count_column = func.coalesce(active_member_counts.c.member_count, 0)
            ordered_stmt = stmt.outerjoin(
                active_member_counts, active_member_counts.c.community_id == CommunityModel.id
            ).order_by(
                member_count_column.desc() if sort_order == "desc" else member_count_column.asc()
            )
        else:
            column = self._SORT_COLUMNS.get(sort_by, CommunityModel.created_at)
            ordered_stmt = apply_sort(stmt, column, sort_order)

        paginated_stmt = apply_pagination(ordered_stmt, offset=offset, limit=limit)
        models = (await self._session.execute(paginated_stmt)).scalars().all()
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

    async def count_active(self, community_id: UUID) -> int:
        stmt = select(func.count()).where(
            CommunityMemberModel.community_id == community_id,
            CommunityMemberModel.status == CommunityMemberStatus.ACTIVE,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def list_by_roles(
        self,
        community_id: UUID,
        roles: Sequence[CommunityRole],
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[CommunityMember]:
        stmt = (
            select(CommunityMemberModel)
            .where(
                CommunityMemberModel.community_id == community_id,
                CommunityMemberModel.role.in_(roles),
                CommunityMemberModel.status == CommunityMemberStatus.ACTIVE,
            )
            .order_by(CommunityMemberModel.joined_at)
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_member_to_domain(model) for model in models]

    async def add(self, member: CommunityMember) -> None:
        model = await self._session.get(CommunityMemberModel, member.id)
        if model is None:
            model = CommunityMemberModel()
            self._session.add(model)
        apply_community_member_to_model(member, model)


class SqlAlchemyCommunityCategoryRepository(CommunityCategoryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, category_id: UUID) -> CommunityCategory | None:
        model = await self._session.get(CommunityCategoryModel, category_id)
        return community_category_to_domain(model) if model is not None else None

    async def get_by_slug(self, slug: str) -> CommunityCategory | None:
        stmt = select(CommunityCategoryModel).where(
            CommunityCategoryModel.slug == slug.strip().lower()
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return community_category_to_domain(model) if model is not None else None

    async def get_by_name(self, name: str) -> CommunityCategory | None:
        stmt = select(CommunityCategoryModel).where(CommunityCategoryModel.name == name.strip())
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return community_category_to_domain(model) if model is not None else None

    async def list_active(self, *, offset: int = 0, limit: int = 100) -> list[CommunityCategory]:
        stmt = (
            select(CommunityCategoryModel)
            .where(CommunityCategoryModel.is_active.is_(True))
            .order_by(CommunityCategoryModel.name)
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_category_to_domain(model) for model in models]

    async def add(self, category: CommunityCategory) -> None:
        model = await self._session.get(CommunityCategoryModel, category.id)
        if model is None:
            model = CommunityCategoryModel()
            self._session.add(model)
        apply_community_category_to_model(category, model)


class SqlAlchemyCommunityTagRepository(CommunityTagRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, tag_id: UUID) -> CommunityTag | None:
        model = await self._session.get(CommunityTagModel, tag_id)
        return community_tag_to_domain(model) if model is not None else None

    async def get_by_name(self, name: str) -> CommunityTag | None:
        stmt = select(CommunityTagModel).where(CommunityTagModel.name == name.strip().lower())
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return community_tag_to_domain(model) if model is not None else None

    async def search(
        self, term: str, *, offset: int = 0, limit: int = 20
    ) -> tuple[Sequence[CommunityTag], int]:
        stmt = select(CommunityTagModel)
        stmt = apply_partial_text_search(stmt, [CommunityTagModel.name], term)
        total = await count_total(self._session, stmt)
        stmt = apply_sort(stmt, CommunityTagModel.name, "asc")
        stmt = apply_pagination(stmt, offset=offset, limit=limit)
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_tag_to_domain(model) for model in models], total

    async def add(self, tag: CommunityTag) -> None:
        model = await self._session.get(CommunityTagModel, tag.id)
        if model is None:
            model = CommunityTagModel()
            self._session.add(model)
        apply_community_tag_to_model(tag, model)

    async def assign(self, community_id: UUID, tag_id: UUID) -> None:
        stmt = select(CommunityTagAssignmentModel).where(
            CommunityTagAssignmentModel.community_id == community_id,
            CommunityTagAssignmentModel.tag_id == tag_id,
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is None:
            self._session.add(CommunityTagAssignmentModel(community_id=community_id, tag_id=tag_id))

    async def unassign(self, community_id: UUID, tag_id: UUID) -> None:
        stmt = select(CommunityTagAssignmentModel).where(
            CommunityTagAssignmentModel.community_id == community_id,
            CommunityTagAssignmentModel.tag_id == tag_id,
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            await self._session.delete(existing)

    async def is_assigned(self, community_id: UUID, tag_id: UUID) -> bool:
        stmt = select(func.count()).where(
            CommunityTagAssignmentModel.community_id == community_id,
            CommunityTagAssignmentModel.tag_id == tag_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0

    async def list_for_community(self, community_id: UUID) -> list[CommunityTag]:
        stmt = (
            select(CommunityTagModel)
            .join(
                CommunityTagAssignmentModel,
                CommunityTagAssignmentModel.tag_id == CommunityTagModel.id,
            )
            .where(CommunityTagAssignmentModel.community_id == community_id)
            .order_by(CommunityTagModel.name)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_tag_to_domain(model) for model in models]


class SqlAlchemyCommunityRuleRepository(CommunityRuleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, rule_id: UUID) -> CommunityRule | None:
        model = await self._session.get(CommunityRuleModel, rule_id)
        return community_rule_to_domain(model) if model is not None else None

    async def list_by_community(
        self, community_id: UUID, *, include_disabled: bool = True
    ) -> list[CommunityRule]:
        stmt = select(CommunityRuleModel).where(CommunityRuleModel.community_id == community_id)
        if not include_disabled:
            stmt = stmt.where(CommunityRuleModel.is_enabled.is_(True))
        stmt = stmt.order_by(CommunityRuleModel.position)
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_rule_to_domain(model) for model in models]

    async def count_by_community(self, community_id: UUID) -> int:
        stmt = select(func.count()).where(CommunityRuleModel.community_id == community_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def add(self, rule: CommunityRule) -> None:
        model = await self._session.get(CommunityRuleModel, rule.id)
        if model is None:
            model = CommunityRuleModel()
            self._session.add(model)
        apply_community_rule_to_model(rule, model)

    async def remove(self, rule_id: UUID) -> None:
        model = await self._session.get(CommunityRuleModel, rule_id)
        if model is not None:
            await self._session.delete(model)
