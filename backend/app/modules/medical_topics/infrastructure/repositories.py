"""Concrete SQLAlchemy repository implementations.

Every `add()` below is "upsert": look up the row by id, create it if
missing, then overwrite its mapped columns from the domain entity's
current in-memory state — see the identical pattern (and rationale) in
`app.modules.community.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.infrastructure.database.query_utils import (
    apply_combined_text_search,
    apply_equality,
    apply_in_filter,
    apply_pagination,
    apply_partial_text_search,
    apply_sort,
    count_total,
    exclude_soft_deleted,
)
from app.modules.medical_topics.domain.entities import (
    MedicalTopic,
    MedicalTopicAlias,
    MedicalTopicFollower,
    MedicalTopicRelation,
    TopicSpecialty,
)
from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility
from app.modules.medical_topics.domain.repositories import (
    MedicalTopicAliasRepository,
    MedicalTopicFollowerRepository,
    MedicalTopicRelationRepository,
    MedicalTopicRepository,
    TopicSpecialtyRepository,
)
from app.modules.medical_topics.infrastructure.mappers import (
    apply_medical_topic_alias_to_model,
    apply_medical_topic_follower_to_model,
    apply_medical_topic_relation_to_model,
    apply_medical_topic_to_model,
    apply_topic_specialty_to_model,
    medical_topic_alias_to_domain,
    medical_topic_follower_to_domain,
    medical_topic_relation_to_domain,
    medical_topic_to_domain,
    topic_specialty_to_domain,
)
from app.modules.medical_topics.infrastructure.models import (
    MedicalTopicAliasModel,
    MedicalTopicFollowerModel,
    MedicalTopicModel,
    MedicalTopicRelationModel,
    TopicSpecialtyModel,
)


class SqlAlchemyMedicalTopicRepository(MedicalTopicRepository):
    _SORT_COLUMNS: dict[str, InstrumentedAttribute[Any]] = {
        "created_at": MedicalTopicModel.created_at,
        "updated_at": MedicalTopicModel.updated_at,
        "name": MedicalTopicModel.name,
        "trending_score": MedicalTopicModel.trending_score,
        "popularity_score": MedicalTopicModel.popularity_score,
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, topic_id: UUID) -> MedicalTopic | None:
        model = await self._session.get(MedicalTopicModel, topic_id)
        if model is None or model.deleted_at is not None:
            return None
        return medical_topic_to_domain(model)

    async def get_by_slug(self, slug: str) -> MedicalTopic | None:
        stmt = select(MedicalTopicModel).where(
            MedicalTopicModel.slug == slug.strip().lower(), MedicalTopicModel.deleted_at.is_(None)
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return medical_topic_to_domain(model) if model is not None else None

    async def list_children(
        self, parent_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[MedicalTopic]:
        stmt = (
            select(MedicalTopicModel)
            .where(MedicalTopicModel.parent_id == parent_id, MedicalTopicModel.deleted_at.is_(None))
            .order_by(MedicalTopicModel.name)
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [medical_topic_to_domain(model) for model in models]

    async def search(
        self,
        *,
        query: str | None = None,
        status: Sequence[TopicStatus] | None = None,
        visibility: Sequence[TopicVisibility] | None = None,
        specialty_id: UUID | None = None,
        parent_id: UUID | None = None,
        featured_only: bool = False,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[MedicalTopic], int]:
        stmt = select(MedicalTopicModel)
        stmt = exclude_soft_deleted(
            stmt, MedicalTopicModel.deleted_at, include_deleted=include_deleted
        )
        stmt = apply_in_filter(stmt, MedicalTopicModel.status, status)
        stmt = apply_in_filter(stmt, MedicalTopicModel.visibility, visibility)
        stmt = apply_equality(stmt, MedicalTopicModel.specialty_id, specialty_id)
        stmt = apply_equality(stmt, MedicalTopicModel.parent_id, parent_id)
        if featured_only:
            stmt = stmt.where(MedicalTopicModel.is_featured.is_(True))
        stmt = apply_combined_text_search(
            stmt,
            full_text_columns=[MedicalTopicModel.name, MedicalTopicModel.description],
            partial_columns=[MedicalTopicModel.name],
            term=query,
        )

        total = await count_total(self._session, stmt)

        column = self._SORT_COLUMNS.get(sort_by, MedicalTopicModel.created_at)
        ordered_stmt = apply_sort(stmt, column, sort_order)
        paginated_stmt = apply_pagination(ordered_stmt, offset=offset, limit=limit)
        models = (await self._session.execute(paginated_stmt)).scalars().all()
        return [medical_topic_to_domain(model) for model in models], total

    async def list_by_ids(self, topic_ids: Sequence[UUID]) -> list[MedicalTopic]:
        if not topic_ids:
            return []
        stmt = select(MedicalTopicModel).where(
            MedicalTopicModel.id.in_(topic_ids), MedicalTopicModel.deleted_at.is_(None)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [medical_topic_to_domain(model) for model in models]

    async def add(self, topic: MedicalTopic) -> None:
        model = await self._session.get(MedicalTopicModel, topic.id)
        if model is None:
            model = MedicalTopicModel()
            self._session.add(model)
        apply_medical_topic_to_model(topic, model)

    async def remove(self, topic_id: UUID) -> None:
        model = await self._session.get(MedicalTopicModel, topic_id)
        if model is not None and model.deleted_at is None:
            model.deleted_at = datetime.now(UTC)


class SqlAlchemyTopicSpecialtyRepository(TopicSpecialtyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, specialty_id: UUID) -> TopicSpecialty | None:
        model = await self._session.get(TopicSpecialtyModel, specialty_id)
        return topic_specialty_to_domain(model) if model is not None else None

    async def get_by_slug(self, slug: str) -> TopicSpecialty | None:
        stmt = select(TopicSpecialtyModel).where(TopicSpecialtyModel.slug == slug.strip().lower())
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return topic_specialty_to_domain(model) if model is not None else None

    async def get_by_name(self, name: str) -> TopicSpecialty | None:
        stmt = select(TopicSpecialtyModel).where(TopicSpecialtyModel.name == name.strip())
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return topic_specialty_to_domain(model) if model is not None else None

    async def list_active(self, *, offset: int = 0, limit: int = 100) -> list[TopicSpecialty]:
        stmt = (
            select(TopicSpecialtyModel)
            .where(TopicSpecialtyModel.is_active.is_(True))
            .order_by(TopicSpecialtyModel.name)
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [topic_specialty_to_domain(model) for model in models]

    async def add(self, specialty: TopicSpecialty) -> None:
        model = await self._session.get(TopicSpecialtyModel, specialty.id)
        if model is None:
            model = TopicSpecialtyModel()
            self._session.add(model)
        apply_topic_specialty_to_model(specialty, model)


class SqlAlchemyMedicalTopicFollowerRepository(MedicalTopicFollowerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_topic_and_user(
        self, topic_id: UUID, user_id: UUID
    ) -> MedicalTopicFollower | None:
        stmt = select(MedicalTopicFollowerModel).where(
            MedicalTopicFollowerModel.topic_id == topic_id,
            MedicalTopicFollowerModel.user_id == user_id,
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return medical_topic_follower_to_domain(model) if model is not None else None

    async def list_by_topic(
        self, topic_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[MedicalTopicFollower]:
        stmt = (
            select(MedicalTopicFollowerModel)
            .where(MedicalTopicFollowerModel.topic_id == topic_id)
            .order_by(MedicalTopicFollowerModel.created_at)
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [medical_topic_follower_to_domain(model) for model in models]

    async def list_by_user(
        self, user_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[MedicalTopicFollower]:
        stmt = (
            select(MedicalTopicFollowerModel)
            .where(MedicalTopicFollowerModel.user_id == user_id)
            .order_by(MedicalTopicFollowerModel.created_at)
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [medical_topic_follower_to_domain(model) for model in models]

    async def count_by_topic(self, topic_id: UUID) -> int:
        stmt = select(MedicalTopicFollowerModel).where(
            MedicalTopicFollowerModel.topic_id == topic_id
        )
        total = await count_total(self._session, stmt)
        return total

    async def add(self, follower: MedicalTopicFollower) -> None:
        model = await self._session.get(MedicalTopicFollowerModel, follower.id)
        if model is None:
            model = MedicalTopicFollowerModel()
            self._session.add(model)
        apply_medical_topic_follower_to_model(follower, model)

    async def remove(self, topic_id: UUID, user_id: UUID) -> None:
        stmt = select(MedicalTopicFollowerModel).where(
            MedicalTopicFollowerModel.topic_id == topic_id,
            MedicalTopicFollowerModel.user_id == user_id,
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)


class SqlAlchemyMedicalTopicAliasRepository(MedicalTopicAliasRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, alias_id: UUID) -> MedicalTopicAlias | None:
        model = await self._session.get(MedicalTopicAliasModel, alias_id)
        return medical_topic_alias_to_domain(model) if model is not None else None

    async def list_by_topic(self, topic_id: UUID) -> list[MedicalTopicAlias]:
        stmt = (
            select(MedicalTopicAliasModel)
            .where(MedicalTopicAliasModel.topic_id == topic_id)
            .order_by(MedicalTopicAliasModel.alias)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [medical_topic_alias_to_domain(model) for model in models]

    async def search_by_alias(
        self, term: str, *, offset: int = 0, limit: int = 20
    ) -> tuple[Sequence[MedicalTopicAlias], int]:
        stmt = select(MedicalTopicAliasModel)
        stmt = apply_partial_text_search(stmt, [MedicalTopicAliasModel.alias], term)
        total = await count_total(self._session, stmt)
        stmt = stmt.order_by(MedicalTopicAliasModel.alias)
        stmt = apply_pagination(stmt, offset=offset, limit=limit)
        models = (await self._session.execute(stmt)).scalars().all()
        return [medical_topic_alias_to_domain(model) for model in models], total

    async def add(self, alias: MedicalTopicAlias) -> None:
        model = await self._session.get(MedicalTopicAliasModel, alias.id)
        if model is None:
            model = MedicalTopicAliasModel()
            self._session.add(model)
        apply_medical_topic_alias_to_model(alias, model)

    async def remove(self, alias_id: UUID) -> None:
        model = await self._session.get(MedicalTopicAliasModel, alias_id)
        if model is not None:
            await self._session.delete(model)


class SqlAlchemyMedicalTopicRelationRepository(MedicalTopicRelationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, relation_id: UUID) -> MedicalTopicRelation | None:
        model = await self._session.get(MedicalTopicRelationModel, relation_id)
        return medical_topic_relation_to_domain(model) if model is not None else None

    async def list_related(self, topic_id: UUID) -> list[MedicalTopicRelation]:
        stmt = select(MedicalTopicRelationModel).where(
            or_(
                MedicalTopicRelationModel.topic_id == topic_id,
                MedicalTopicRelationModel.related_topic_id == topic_id,
            )
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [medical_topic_relation_to_domain(model) for model in models]

    async def exists(self, topic_id: UUID, related_topic_id: UUID) -> bool:
        stmt = select(MedicalTopicRelationModel).where(
            or_(
                and_(
                    MedicalTopicRelationModel.topic_id == topic_id,
                    MedicalTopicRelationModel.related_topic_id == related_topic_id,
                ),
                and_(
                    MedicalTopicRelationModel.topic_id == related_topic_id,
                    MedicalTopicRelationModel.related_topic_id == topic_id,
                ),
            )
        )
        total = await count_total(self._session, stmt)
        return total > 0

    async def add(self, relation: MedicalTopicRelation) -> None:
        model = await self._session.get(MedicalTopicRelationModel, relation.id)
        if model is None:
            model = MedicalTopicRelationModel()
            self._session.add(model)
        apply_medical_topic_relation_to_model(relation, model)

    async def remove(self, relation_id: UUID) -> None:
        model = await self._session.get(MedicalTopicRelationModel, relation_id)
        if model is not None:
            await self._session.delete(model)
