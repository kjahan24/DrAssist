"""Concrete SQLAlchemy repository implementations.

Every `add()` below is "upsert": look up the row by id, create it if
missing, then overwrite its mapped columns from the domain entity's
current in-memory state — see the identical pattern (and rationale) in
every prior module's own `infrastructure/repositories.py`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

import base64
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import Select, and_, or_, select
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
    exclude_soft_deleted,
)
from app.modules.community_posts.domain.entities import (
    CommunityPost,
    CommunityPostAttachment,
    CommunityPostTag,
    CommunityPostTopic,
)
from app.modules.community_posts.domain.enums import PostStatus, PostType, PostVisibility
from app.modules.community_posts.domain.repositories import (
    CommunityPostAttachmentRepository,
    CommunityPostRepository,
    CommunityPostTagRepository,
    CommunityPostTopicRepository,
)
from app.modules.community_posts.infrastructure.mappers import (
    apply_community_post_attachment_to_model,
    apply_community_post_tag_to_model,
    apply_community_post_to_model,
    apply_community_post_topic_to_model,
    community_post_attachment_to_domain,
    community_post_tag_to_domain,
    community_post_to_domain,
    community_post_topic_to_domain,
)
from app.modules.community_posts.infrastructure.models import (
    CommunityPostAttachmentModel,
    CommunityPostModel,
    CommunityPostTagModel,
    CommunityPostTopicModel,
)

_CURSOR_SEPARATOR = "|"


def _encode_cursor(published_at: datetime, post_id: UUID) -> str:
    payload = f"{published_at.isoformat()}{_CURSOR_SEPARATOR}{post_id}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    payload = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    published_at_raw, post_id_raw = payload.split(_CURSOR_SEPARATOR, 1)
    return datetime.fromisoformat(published_at_raw), UUID(post_id_raw)


class SqlAlchemyCommunityPostRepository(CommunityPostRepository):
    """`browse_feed`'s keyset ("cursor") pagination sorts by
    `(published_at DESC, id DESC)` — `id` (a UUID, not a monotonic
    integer, but stable/unique) is the tiebreaker for posts published in
    the same instant, exactly the "sort column + unique tiebreaker" shape
    every keyset-pagination scheme needs to guarantee a strict, gapless
    ordering. `cursor` opaquely encodes that pair (see `_encode_cursor`/
    `_decode_cursor`).

    `pinned_first=True` (community feed only) shows every pinned post on
    the *first* page only (`cursor is None`), ahead of the normal keyset-
    paginated stream, and never repeats them on later pages — the same
    "stickied posts shown once, not re-injected every page" behavior
    Reddit's own subreddit front page already has. One documented
    simplification: if pinned posts alone fill an entire page (`limit`),
    this implementation does not also probe for further regular posts
    that page — a case that would need `limit`-or-more simultaneously
    pinned posts in one community, far beyond realistic moderation use.
    """

    _SORT_COLUMNS: dict[str, InstrumentedAttribute[Any]] = {
        "created_at": CommunityPostModel.created_at,
        "updated_at": CommunityPostModel.updated_at,
        "published_at": CommunityPostModel.published_at,
        "title": CommunityPostModel.title,
        "view_count": CommunityPostModel.view_count,
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, post_id: UUID) -> CommunityPost | None:
        model = await self._session.get(CommunityPostModel, post_id)
        if model is None or model.deleted_at is not None:
            return None
        return community_post_to_domain(model)

    async def get_by_slug(self, community_id: UUID, slug: str) -> CommunityPost | None:
        stmt = select(CommunityPostModel).where(
            CommunityPostModel.community_id == community_id,
            CommunityPostModel.slug == slug.strip().lower(),
            CommunityPostModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return community_post_to_domain(model) if model is not None else None

    def _topic_scoped_post_ids(self, topic_id: UUID) -> Select[Any]:
        return select(CommunityPostTopicModel.post_id).where(
            CommunityPostTopicModel.topic_id == topic_id
        )

    async def search(
        self,
        *,
        organization_id: UUID,
        community_id: UUID | None = None,
        topic_id: UUID | None = None,
        author_id: UUID | None = None,
        post_type: Sequence[PostType] | None = None,
        status: Sequence[PostStatus] | None = None,
        visibility: Sequence[PostVisibility] | None = None,
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
    ) -> tuple[Sequence[CommunityPost], int]:
        stmt = select(CommunityPostModel).where(
            CommunityPostModel.organization_id == organization_id
        )
        stmt = exclude_soft_deleted(
            stmt, CommunityPostModel.deleted_at, include_deleted=include_deleted
        )
        stmt = apply_equality(stmt, CommunityPostModel.community_id, community_id)
        stmt = apply_equality(stmt, CommunityPostModel.author_id, author_id)
        stmt = apply_in_filter(stmt, CommunityPostModel.post_type, post_type)
        stmt = apply_in_filter(stmt, CommunityPostModel.status, status)
        stmt = apply_in_filter(stmt, CommunityPostModel.visibility, visibility)
        if pinned_only:
            stmt = stmt.where(CommunityPostModel.is_pinned.is_(True))
        if featured_only:
            stmt = stmt.where(CommunityPostModel.is_featured.is_(True))
        if topic_id is not None:
            stmt = stmt.where(CommunityPostModel.id.in_(self._topic_scoped_post_ids(topic_id)))
        stmt = apply_date_range(
            stmt, CommunityPostModel.created_at, start=created_from, end=created_to
        )
        stmt = apply_combined_text_search(
            stmt,
            full_text_columns=[
                CommunityPostModel.title,
                CommunityPostModel.body,
                CommunityPostModel.excerpt,
            ],
            partial_columns=[CommunityPostModel.title],
            term=query,
        )

        total = await count_total(self._session, stmt)

        column = self._SORT_COLUMNS.get(sort_by, CommunityPostModel.created_at)
        ordered_stmt = apply_sort(stmt, column, sort_order)
        paginated_stmt = apply_pagination(ordered_stmt, offset=offset, limit=limit)
        models = (await self._session.execute(paginated_stmt)).scalars().all()
        return [community_post_to_domain(model) for model in models], total

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
    ) -> tuple[Sequence[CommunityPost], str | None]:
        base_conditions: list[Any] = [
            CommunityPostModel.organization_id == organization_id,
            CommunityPostModel.status == PostStatus.PUBLISHED,
            CommunityPostModel.deleted_at.is_(None),
        ]
        if community_id is not None:
            base_conditions.append(CommunityPostModel.community_id == community_id)
        if author_id is not None:
            base_conditions.append(CommunityPostModel.author_id == author_id)
        if topic_id is not None:
            base_conditions.append(CommunityPostModel.id.in_(self._topic_scoped_post_ids(topic_id)))

        pinned_models: list[CommunityPostModel] = []
        if pinned_first and cursor is None:
            pinned_stmt = (
                select(CommunityPostModel)
                .where(*base_conditions, CommunityPostModel.is_pinned.is_(True))
                .order_by(CommunityPostModel.published_at.desc(), CommunityPostModel.id.desc())
            )
            pinned_models = list((await self._session.execute(pinned_stmt)).scalars().all())

        remaining = limit - len(pinned_models)
        regular_models: list[CommunityPostModel] = []
        regular_has_more = False
        if remaining > 0:
            regular_conditions = list(base_conditions)
            if pinned_first:
                regular_conditions.append(CommunityPostModel.is_pinned.is_(False))
            if cursor is not None:
                cursor_published_at, cursor_id = _decode_cursor(cursor)
                regular_conditions.append(
                    or_(
                        CommunityPostModel.published_at < cursor_published_at,
                        and_(
                            CommunityPostModel.published_at == cursor_published_at,
                            CommunityPostModel.id < cursor_id,
                        ),
                    )
                )
            regular_stmt = (
                select(CommunityPostModel)
                .where(*regular_conditions)
                .order_by(CommunityPostModel.published_at.desc(), CommunityPostModel.id.desc())
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

        return [community_post_to_domain(model) for model in page_models], next_cursor

    async def add(self, post: CommunityPost) -> None:
        model = await self._session.get(CommunityPostModel, post.id)
        if model is None:
            model = CommunityPostModel()
            self._session.add(model)
        apply_community_post_to_model(post, model)

    async def remove(self, post_id: UUID) -> None:
        model = await self._session.get(CommunityPostModel, post_id)
        if model is not None and model.deleted_at is None:
            model.deleted_at = datetime.now(UTC)


class SqlAlchemyCommunityPostTopicRepository(CommunityPostTopicRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, post_topic_id: UUID) -> CommunityPostTopic | None:
        model = await self._session.get(CommunityPostTopicModel, post_topic_id)
        return community_post_topic_to_domain(model) if model is not None else None

    async def list_by_post(self, post_id: UUID) -> list[CommunityPostTopic]:
        stmt = select(CommunityPostTopicModel).where(CommunityPostTopicModel.post_id == post_id)
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_post_topic_to_domain(model) for model in models]

    async def list_post_ids_by_topic(
        self, topic_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[UUID]:
        stmt = (
            select(CommunityPostTopicModel.post_id)
            .where(CommunityPostTopicModel.topic_id == topic_id)
            .order_by(CommunityPostTopicModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def is_assigned(self, post_id: UUID, topic_id: UUID) -> bool:
        stmt = select(CommunityPostTopicModel).where(
            CommunityPostTopicModel.post_id == post_id, CommunityPostTopicModel.topic_id == topic_id
        )
        total = await count_total(self._session, stmt)
        return total > 0

    async def add(self, assignment: CommunityPostTopic) -> None:
        model = await self._session.get(CommunityPostTopicModel, assignment.id)
        if model is None:
            model = CommunityPostTopicModel()
            self._session.add(model)
        apply_community_post_topic_to_model(assignment, model)

    async def remove(self, post_topic_id: UUID) -> None:
        model = await self._session.get(CommunityPostTopicModel, post_topic_id)
        if model is not None:
            await self._session.delete(model)


class SqlAlchemyCommunityPostTagRepository(CommunityPostTagRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, post_tag_id: UUID) -> CommunityPostTag | None:
        model = await self._session.get(CommunityPostTagModel, post_tag_id)
        return community_post_tag_to_domain(model) if model is not None else None

    async def list_by_post(self, post_id: UUID) -> list[CommunityPostTag]:
        stmt = select(CommunityPostTagModel).where(CommunityPostTagModel.post_id == post_id)
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_post_tag_to_domain(model) for model in models]

    async def is_assigned(self, post_id: UUID, tag: str) -> bool:
        stmt = select(CommunityPostTagModel).where(
            CommunityPostTagModel.post_id == post_id,
            CommunityPostTagModel.tag == tag.strip().lower(),
        )
        total = await count_total(self._session, stmt)
        return total > 0

    async def add(self, assignment: CommunityPostTag) -> None:
        model = await self._session.get(CommunityPostTagModel, assignment.id)
        if model is None:
            model = CommunityPostTagModel()
            self._session.add(model)
        apply_community_post_tag_to_model(assignment, model)

    async def remove(self, post_tag_id: UUID) -> None:
        model = await self._session.get(CommunityPostTagModel, post_tag_id)
        if model is not None:
            await self._session.delete(model)


class SqlAlchemyCommunityPostAttachmentRepository(CommunityPostAttachmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, attachment_id: UUID) -> CommunityPostAttachment | None:
        model = await self._session.get(CommunityPostAttachmentModel, attachment_id)
        return community_post_attachment_to_domain(model) if model is not None else None

    async def list_by_post(self, post_id: UUID) -> list[CommunityPostAttachment]:
        stmt = select(CommunityPostAttachmentModel).where(
            CommunityPostAttachmentModel.post_id == post_id
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_post_attachment_to_domain(model) for model in models]

    async def is_assigned(self, post_id: UUID, document_id: UUID) -> bool:
        stmt = select(CommunityPostAttachmentModel).where(
            CommunityPostAttachmentModel.post_id == post_id,
            CommunityPostAttachmentModel.document_id == document_id,
        )
        total = await count_total(self._session, stmt)
        return total > 0

    async def add(self, attachment: CommunityPostAttachment) -> None:
        model = await self._session.get(CommunityPostAttachmentModel, attachment.id)
        if model is None:
            model = CommunityPostAttachmentModel()
            self._session.add(model)
        apply_community_post_attachment_to_model(attachment, model)

    async def remove(self, attachment_id: UUID) -> None:
        model = await self._session.get(CommunityPostAttachmentModel, attachment_id)
        if model is not None:
            await self._session.delete(model)
