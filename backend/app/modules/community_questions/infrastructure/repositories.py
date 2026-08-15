"""Concrete SQLAlchemy repository implementations.

Every `add()` below is "upsert": look up the row by id, create it if
missing, then overwrite its mapped columns from the domain entity's
current in-memory state — see the identical pattern in
`app.modules.community_posts.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

import base64
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.infrastructure.database.query_utils import (
    apply_combined_text_search,
    apply_date_range,
    apply_equality,
    apply_in_filter,
    apply_pagination,
    apply_sort,
    count_total,
)
from app.modules.community_questions.domain.entities import (
    CommunityQuestion,
    CommunityQuestionAttachment,
    CommunityQuestionFollower,
    CommunityQuestionTag,
    CommunityQuestionTopic,
)
from app.modules.community_questions.domain.enums import (
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)
from app.modules.community_questions.domain.repositories import (
    CommunityQuestionAttachmentRepository,
    CommunityQuestionFollowerRepository,
    CommunityQuestionRepository,
    CommunityQuestionTagRepository,
    CommunityQuestionTopicRepository,
)
from app.modules.community_questions.infrastructure.mappers import (
    apply_community_question_attachment_to_model,
    apply_community_question_follower_to_model,
    apply_community_question_tag_to_model,
    apply_community_question_to_model,
    apply_community_question_topic_to_model,
    community_question_attachment_to_domain,
    community_question_follower_to_domain,
    community_question_tag_to_domain,
    community_question_to_domain,
    community_question_topic_to_domain,
)
from app.modules.community_questions.infrastructure.models import (
    CommunityQuestionAttachmentModel,
    CommunityQuestionFollowerModel,
    CommunityQuestionModel,
    CommunityQuestionTagModel,
    CommunityQuestionTopicModel,
)

_CURSOR_SEPARATOR = "|"
_LIVE_FEED_STATUSES = (QuestionStatus.PUBLISHED, QuestionStatus.CLOSED)


def _encode_cursor(published_at: datetime, question_id: UUID) -> str:
    payload = f"{published_at.isoformat()}{_CURSOR_SEPARATOR}{question_id}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    payload = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    published_at_raw, question_id_raw = payload.split(_CURSOR_SEPARATOR, 1)
    return datetime.fromisoformat(published_at_raw), UUID(question_id_raw)


class SqlAlchemyCommunityQuestionRepository(CommunityQuestionRepository):
    """`browse_feed`'s keyset ("cursor") pagination sorts by
    `(published_at DESC, id DESC)` — the same shape
    `SqlAlchemyCommunityPostRepository.browse_feed` already establishes,
    see that class's own docstring for the full reasoning.

    No `remove()` method: see `CommunityQuestionRepository`'s own
    docstring — deletion is the `CommunityQuestion.delete()` status
    transition, persisted through the ordinary `add()` upsert.
    """

    _SORT_COLUMNS: dict[str, InstrumentedAttribute[Any]] = {
        "created_at": CommunityQuestionModel.created_at,
        "updated_at": CommunityQuestionModel.updated_at,
        "published_at": CommunityQuestionModel.published_at,
        "title": CommunityQuestionModel.title,
        "view_count": CommunityQuestionModel.view_count,
        "follower_count": CommunityQuestionModel.follower_count,
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, question_id: UUID) -> CommunityQuestion | None:
        model = await self._session.get(CommunityQuestionModel, question_id)
        return community_question_to_domain(model) if model is not None else None

    async def get_by_slug(self, community_id: UUID, slug: str) -> CommunityQuestion | None:
        stmt = select(CommunityQuestionModel).where(
            CommunityQuestionModel.community_id == community_id,
            CommunityQuestionModel.slug == slug.strip().lower(),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return community_question_to_domain(model) if model is not None else None

    def _topic_scoped_filter(self, topic_id: UUID) -> ColumnElement[bool]:
        """A question matches `topic_id` if it is either the question's
        own mandatory `primary_topic_id`, or a *secondary* assignment in
        `community_question_topics` — see `CommunityQuestionRepository`'s
        own docstring for why both places must be checked."""
        secondary_match = select(CommunityQuestionTopicModel.question_id).where(
            CommunityQuestionTopicModel.topic_id == topic_id
        )
        return or_(
            CommunityQuestionModel.primary_topic_id == topic_id,
            CommunityQuestionModel.id.in_(secondary_match),
        )

    async def search(
        self,
        *,
        organization_id: UUID,
        community_id: UUID | None = None,
        topic_id: UUID | None = None,
        author_id: UUID | None = None,
        question_type: Sequence[QuestionType] | None = None,
        status: Sequence[QuestionStatus] | None = None,
        visibility: Sequence[QuestionVisibility] | None = None,
        pinned_only: bool = False,
        featured_only: bool = False,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        query: str | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[CommunityQuestion], int]:
        stmt = select(CommunityQuestionModel).where(
            CommunityQuestionModel.organization_id == organization_id
        )
        if not include_deleted:
            stmt = stmt.where(CommunityQuestionModel.status != QuestionStatus.DELETED)
        stmt = apply_equality(stmt, CommunityQuestionModel.community_id, community_id)
        stmt = apply_equality(stmt, CommunityQuestionModel.author_id, author_id)
        stmt = apply_in_filter(stmt, CommunityQuestionModel.question_type, question_type)
        stmt = apply_in_filter(stmt, CommunityQuestionModel.status, status)
        stmt = apply_in_filter(stmt, CommunityQuestionModel.visibility, visibility)
        if pinned_only:
            stmt = stmt.where(CommunityQuestionModel.is_pinned.is_(True))
        if featured_only:
            stmt = stmt.where(CommunityQuestionModel.is_featured.is_(True))
        if topic_id is not None:
            stmt = stmt.where(self._topic_scoped_filter(topic_id))
        stmt = apply_date_range(
            stmt, CommunityQuestionModel.created_at, start=created_from, end=created_to
        )
        stmt = apply_combined_text_search(
            stmt,
            full_text_columns=[
                CommunityQuestionModel.title,
                CommunityQuestionModel.body,
                CommunityQuestionModel.summary,
            ],
            partial_columns=[CommunityQuestionModel.title],
            term=query,
        )

        total = await count_total(self._session, stmt)

        column = self._SORT_COLUMNS.get(sort_by, CommunityQuestionModel.created_at)
        ordered_stmt = apply_sort(stmt, column, sort_order)
        paginated_stmt = apply_pagination(ordered_stmt, offset=offset, limit=limit)
        models = (await self._session.execute(paginated_stmt)).scalars().all()
        return [community_question_to_domain(model) for model in models], total

    async def browse_feed(
        self,
        *,
        organization_id: UUID,
        community_id: UUID | None = None,
        topic_id: UUID | None = None,
        author_id: UUID | None = None,
        pinned_first: bool = False,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[Sequence[CommunityQuestion], str | None]:
        base_conditions: list[Any] = [
            CommunityQuestionModel.organization_id == organization_id,
            CommunityQuestionModel.status.in_(_LIVE_FEED_STATUSES),
        ]
        if community_id is not None:
            base_conditions.append(CommunityQuestionModel.community_id == community_id)
        if author_id is not None:
            base_conditions.append(CommunityQuestionModel.author_id == author_id)
        if topic_id is not None:
            base_conditions.append(self._topic_scoped_filter(topic_id))

        pinned_models: list[CommunityQuestionModel] = []
        if pinned_first and cursor is None:
            pinned_stmt = (
                select(CommunityQuestionModel)
                .where(*base_conditions, CommunityQuestionModel.is_pinned.is_(True))
                .order_by(
                    CommunityQuestionModel.published_at.desc(), CommunityQuestionModel.id.desc()
                )
            )
            pinned_models = list((await self._session.execute(pinned_stmt)).scalars().all())

        remaining = limit - len(pinned_models)
        regular_models: list[CommunityQuestionModel] = []
        regular_has_more = False
        if remaining > 0:
            regular_conditions = list(base_conditions)
            if pinned_first:
                regular_conditions.append(CommunityQuestionModel.is_pinned.is_(False))
            if cursor is not None:
                cursor_published_at, cursor_id = _decode_cursor(cursor)
                regular_conditions.append(
                    or_(
                        CommunityQuestionModel.published_at < cursor_published_at,
                        and_(
                            CommunityQuestionModel.published_at == cursor_published_at,
                            CommunityQuestionModel.id < cursor_id,
                        ),
                    )
                )
            regular_stmt = (
                select(CommunityQuestionModel)
                .where(*regular_conditions)
                .order_by(
                    CommunityQuestionModel.published_at.desc(), CommunityQuestionModel.id.desc()
                )
                .limit(remaining + 1)
            )
            fetched = list((await self._session.execute(regular_stmt)).scalars().all())
            regular_has_more = len(fetched) > remaining
            regular_models = fetched[:remaining]

        page_models = [*pinned_models, *regular_models]

        next_cursor = None
        if regular_has_more and regular_models:
            last = regular_models[-1]
            assert last.published_at is not None
            next_cursor = _encode_cursor(last.published_at, last.id)

        return [community_question_to_domain(model) for model in page_models], next_cursor

    async def add(self, question: CommunityQuestion) -> None:
        model = await self._session.get(CommunityQuestionModel, question.id)
        if model is None:
            model = CommunityQuestionModel()
            self._session.add(model)
        apply_community_question_to_model(question, model)


class SqlAlchemyCommunityQuestionTopicRepository(CommunityQuestionTopicRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, question_topic_id: UUID) -> CommunityQuestionTopic | None:
        model = await self._session.get(CommunityQuestionTopicModel, question_topic_id)
        return community_question_topic_to_domain(model) if model is not None else None

    async def list_by_question(self, question_id: UUID) -> list[CommunityQuestionTopic]:
        stmt = select(CommunityQuestionTopicModel).where(
            CommunityQuestionTopicModel.question_id == question_id
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_question_topic_to_domain(model) for model in models]

    async def list_question_ids_by_topic(
        self, topic_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[UUID]:
        stmt = (
            select(CommunityQuestionTopicModel.question_id)
            .where(CommunityQuestionTopicModel.topic_id == topic_id)
            .order_by(CommunityQuestionTopicModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def is_assigned(self, question_id: UUID, topic_id: UUID) -> bool:
        stmt = select(CommunityQuestionTopicModel).where(
            CommunityQuestionTopicModel.question_id == question_id,
            CommunityQuestionTopicModel.topic_id == topic_id,
        )
        total = await count_total(self._session, stmt)
        return total > 0

    async def add(self, assignment: CommunityQuestionTopic) -> None:
        model = await self._session.get(CommunityQuestionTopicModel, assignment.id)
        if model is None:
            model = CommunityQuestionTopicModel()
            self._session.add(model)
        apply_community_question_topic_to_model(assignment, model)

    async def remove(self, question_topic_id: UUID) -> None:
        model = await self._session.get(CommunityQuestionTopicModel, question_topic_id)
        if model is not None:
            await self._session.delete(model)


class SqlAlchemyCommunityQuestionTagRepository(CommunityQuestionTagRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, question_tag_id: UUID) -> CommunityQuestionTag | None:
        model = await self._session.get(CommunityQuestionTagModel, question_tag_id)
        return community_question_tag_to_domain(model) if model is not None else None

    async def list_by_question(self, question_id: UUID) -> list[CommunityQuestionTag]:
        stmt = select(CommunityQuestionTagModel).where(
            CommunityQuestionTagModel.question_id == question_id
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_question_tag_to_domain(model) for model in models]

    async def is_assigned(self, question_id: UUID, tag: str) -> bool:
        stmt = select(CommunityQuestionTagModel).where(
            CommunityQuestionTagModel.question_id == question_id,
            CommunityQuestionTagModel.tag == tag.strip().lower(),
        )
        total = await count_total(self._session, stmt)
        return total > 0

    async def add(self, assignment: CommunityQuestionTag) -> None:
        model = await self._session.get(CommunityQuestionTagModel, assignment.id)
        if model is None:
            model = CommunityQuestionTagModel()
            self._session.add(model)
        apply_community_question_tag_to_model(assignment, model)

    async def remove(self, question_tag_id: UUID) -> None:
        model = await self._session.get(CommunityQuestionTagModel, question_tag_id)
        if model is not None:
            await self._session.delete(model)


class SqlAlchemyCommunityQuestionAttachmentRepository(CommunityQuestionAttachmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, attachment_id: UUID) -> CommunityQuestionAttachment | None:
        model = await self._session.get(CommunityQuestionAttachmentModel, attachment_id)
        return community_question_attachment_to_domain(model) if model is not None else None

    async def list_by_question(self, question_id: UUID) -> list[CommunityQuestionAttachment]:
        stmt = select(CommunityQuestionAttachmentModel).where(
            CommunityQuestionAttachmentModel.question_id == question_id
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_question_attachment_to_domain(model) for model in models]

    async def is_assigned(self, question_id: UUID, document_id: UUID) -> bool:
        stmt = select(CommunityQuestionAttachmentModel).where(
            CommunityQuestionAttachmentModel.question_id == question_id,
            CommunityQuestionAttachmentModel.document_id == document_id,
        )
        total = await count_total(self._session, stmt)
        return total > 0

    async def add(self, attachment: CommunityQuestionAttachment) -> None:
        model = await self._session.get(CommunityQuestionAttachmentModel, attachment.id)
        if model is None:
            model = CommunityQuestionAttachmentModel()
            self._session.add(model)
        apply_community_question_attachment_to_model(attachment, model)

    async def remove(self, attachment_id: UUID) -> None:
        model = await self._session.get(CommunityQuestionAttachmentModel, attachment_id)
        if model is not None:
            await self._session.delete(model)


class SqlAlchemyCommunityQuestionFollowerRepository(CommunityQuestionFollowerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, follower_id: UUID) -> CommunityQuestionFollower | None:
        model = await self._session.get(CommunityQuestionFollowerModel, follower_id)
        return community_question_follower_to_domain(model) if model is not None else None

    async def get_by_question_and_user(
        self, question_id: UUID, user_id: UUID
    ) -> CommunityQuestionFollower | None:
        stmt = select(CommunityQuestionFollowerModel).where(
            CommunityQuestionFollowerModel.question_id == question_id,
            CommunityQuestionFollowerModel.user_id == user_id,
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return community_question_follower_to_domain(model) if model is not None else None

    async def list_by_question(
        self, question_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[CommunityQuestionFollower]:
        stmt = (
            select(CommunityQuestionFollowerModel)
            .where(CommunityQuestionFollowerModel.question_id == question_id)
            .order_by(CommunityQuestionFollowerModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_question_follower_to_domain(model) for model in models]

    async def is_following(self, question_id: UUID, user_id: UUID) -> bool:
        stmt = select(CommunityQuestionFollowerModel).where(
            CommunityQuestionFollowerModel.question_id == question_id,
            CommunityQuestionFollowerModel.user_id == user_id,
        )
        total = await count_total(self._session, stmt)
        return total > 0

    async def add(self, follower: CommunityQuestionFollower) -> None:
        model = await self._session.get(CommunityQuestionFollowerModel, follower.id)
        if model is None:
            model = CommunityQuestionFollowerModel()
            self._session.add(model)
        apply_community_question_follower_to_model(follower, model)

    async def remove(self, follower_id: UUID) -> None:
        model = await self._session.get(CommunityQuestionFollowerModel, follower_id)
        if model is not None:
            await self._session.delete(model)
