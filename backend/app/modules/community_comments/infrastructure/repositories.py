"""Concrete SQLAlchemy repository implementations.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern in
`app.modules.community_answers.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

import base64
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.query_utils import apply_combined_text_search, apply_date_range
from app.modules.community_comments.domain.entities import (
    CommunityComment,
    CommunityCommentAttachment,
    CommunityCommentRevision,
)
from app.modules.community_comments.domain.enums import CommentStatus, CommentTargetType
from app.modules.community_comments.domain.repositories import (
    CommunityCommentAttachmentRepository,
    CommunityCommentRepository,
    CommunityCommentRevisionRepository,
)
from app.modules.community_comments.infrastructure.mappers import (
    apply_community_comment_attachment_to_model,
    apply_community_comment_revision_to_model,
    apply_community_comment_to_model,
    community_comment_attachment_to_domain,
    community_comment_revision_to_domain,
    community_comment_to_domain,
)
from app.modules.community_comments.infrastructure.models import (
    CommunityCommentAttachmentModel,
    CommunityCommentModel,
    CommunityCommentRevisionModel,
)

_CURSOR_SEPARATOR = "|"


def _encode_cursor(created_at: datetime, comment_id: UUID) -> str:
    payload = f"{created_at.isoformat()}{_CURSOR_SEPARATOR}{comment_id}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    payload = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    created_at_raw, comment_id_raw = payload.split(_CURSOR_SEPARATOR, 1)
    return datetime.fromisoformat(created_at_raw), UUID(comment_id_raw)


class SqlAlchemyCommunityCommentRepository(CommunityCommentRepository):
    """`browse`'s keyset ("cursor") pagination sorts by `(created_at,
    id)`, ascending or descending per `sort_order` — `created_at`
    (never null) rather than `published_at` (null for drafts), since
    `browse` is also used to list drafts (`include_deleted`/`status`
    filters make this a general-purpose management view too, not only a
    published-only public feed) — see this class's own module's
    `CommunityCommentRepository.browse` docstring.

    No `remove()` method: see `CommunityCommentRepository`'s own
    docstring — deletion is the `CommunityComment.delete()` status
    transition, persisted through the ordinary `add()` upsert.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, comment_id: UUID) -> CommunityComment | None:
        model = await self._session.get(CommunityCommentModel, comment_id)
        return community_comment_to_domain(model) if model is not None else None

    async def browse(
        self,
        *,
        organization_id: UUID,
        target_type: CommentTargetType | None = None,
        target_id: UUID | None = None,
        community_id: UUID | None = None,
        topic_id: UUID | None = None,
        author_id: UUID | None = None,
        parent_comment_id: UUID | None = None,
        top_level_only: bool = False,
        status: Sequence[CommentStatus] | None = None,
        query: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        include_deleted: bool = False,
        sort_order: Literal["asc", "desc"] = "desc",
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[Sequence[CommunityComment], str | None]:
        conditions: list[Any] = [CommunityCommentModel.organization_id == organization_id]
        if not include_deleted:
            conditions.append(CommunityCommentModel.status != CommentStatus.DELETED)
        if target_type is not None:
            conditions.append(CommunityCommentModel.target_type == target_type)
        if target_id is not None:
            conditions.append(CommunityCommentModel.target_id == target_id)
        if community_id is not None:
            conditions.append(CommunityCommentModel.community_id == community_id)
        if topic_id is not None:
            conditions.append(CommunityCommentModel.topic_id == topic_id)
        if author_id is not None:
            conditions.append(CommunityCommentModel.author_id == author_id)
        if parent_comment_id is not None:
            conditions.append(CommunityCommentModel.parent_comment_id == parent_comment_id)
        if top_level_only:
            conditions.append(CommunityCommentModel.parent_comment_id.is_(None))
        if status:
            conditions.append(CommunityCommentModel.status.in_(status))

        stmt = select(CommunityCommentModel).where(*conditions)
        stmt = apply_date_range(
            stmt, CommunityCommentModel.created_at, start=created_from, end=created_to
        )
        stmt = apply_combined_text_search(
            stmt, full_text_columns=[CommunityCommentModel.body], term=query
        )

        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            if sort_order == "desc":
                stmt = stmt.where(
                    or_(
                        CommunityCommentModel.created_at < cursor_created_at,
                        and_(
                            CommunityCommentModel.created_at == cursor_created_at,
                            CommunityCommentModel.id < cursor_id,
                        ),
                    )
                )
            else:
                stmt = stmt.where(
                    or_(
                        CommunityCommentModel.created_at > cursor_created_at,
                        and_(
                            CommunityCommentModel.created_at == cursor_created_at,
                            CommunityCommentModel.id > cursor_id,
                        ),
                    )
                )

        if sort_order == "desc":
            stmt = stmt.order_by(
                CommunityCommentModel.created_at.desc(), CommunityCommentModel.id.desc()
            )
        else:
            stmt = stmt.order_by(
                CommunityCommentModel.created_at.asc(), CommunityCommentModel.id.asc()
            )
        stmt = stmt.limit(limit + 1)

        rows = list((await self._session.execute(stmt)).scalars().all())
        has_more = len(rows) > limit
        page = rows[:limit]

        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = _encode_cursor(last.created_at, last.id)

        return [community_comment_to_domain(m) for m in page], next_cursor

    async def get_thread(
        self,
        root_comment_id: UUID,
        *,
        max_depth: int,
        status: Sequence[CommentStatus] | None = None,
        limit: int = 500,
    ) -> Sequence[CommunityComment]:
        conditions: list[Any] = [
            CommunityCommentModel.root_comment_id == root_comment_id,
            CommunityCommentModel.depth <= max_depth,
        ]
        if status:
            conditions.append(CommunityCommentModel.status.in_(status))

        stmt = (
            select(CommunityCommentModel)
            .where(*conditions)
            .order_by(CommunityCommentModel.depth.asc(), CommunityCommentModel.created_at.asc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [community_comment_to_domain(m) for m in rows]

    async def add(self, comment: CommunityComment) -> None:
        model = await self._session.get(CommunityCommentModel, comment.id)
        if model is None:
            model = CommunityCommentModel()
            self._session.add(model)
        apply_community_comment_to_model(comment, model)


class SqlAlchemyCommunityCommentRevisionRepository(CommunityCommentRevisionRepository):
    """No `remove()` method — see `CommunityCommentRevisionRepository`'s
    own docstring: revision history is immutable."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, revision_id: UUID) -> CommunityCommentRevision | None:
        model = await self._session.get(CommunityCommentRevisionModel, revision_id)
        return community_comment_revision_to_domain(model) if model is not None else None

    async def list_by_comment(
        self, comment_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[CommunityCommentRevision]:
        stmt = (
            select(CommunityCommentRevisionModel)
            .where(CommunityCommentRevisionModel.comment_id == comment_id)
            .order_by(CommunityCommentRevisionModel.revision_number.desc())
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_comment_revision_to_domain(model) for model in models]

    async def add(self, revision: CommunityCommentRevision) -> None:
        model = await self._session.get(CommunityCommentRevisionModel, revision.id)
        if model is None:
            model = CommunityCommentRevisionModel()
            self._session.add(model)
        apply_community_comment_revision_to_model(revision, model)


class SqlAlchemyCommunityCommentAttachmentRepository(CommunityCommentAttachmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, attachment_id: UUID) -> CommunityCommentAttachment | None:
        model = await self._session.get(CommunityCommentAttachmentModel, attachment_id)
        return community_comment_attachment_to_domain(model) if model is not None else None

    async def list_by_comment(self, comment_id: UUID) -> list[CommunityCommentAttachment]:
        stmt = select(CommunityCommentAttachmentModel).where(
            CommunityCommentAttachmentModel.comment_id == comment_id
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_comment_attachment_to_domain(model) for model in models]

    async def is_assigned(self, comment_id: UUID, document_id: UUID) -> bool:
        stmt = select(CommunityCommentAttachmentModel).where(
            CommunityCommentAttachmentModel.comment_id == comment_id,
            CommunityCommentAttachmentModel.document_id == document_id,
        )
        result = (await self._session.execute(stmt)).scalar_one_or_none()
        return result is not None

    async def add(self, attachment: CommunityCommentAttachment) -> None:
        model = await self._session.get(CommunityCommentAttachmentModel, attachment.id)
        if model is None:
            model = CommunityCommentAttachmentModel()
            self._session.add(model)
        apply_community_comment_attachment_to_model(attachment, model)

    async def remove(self, attachment_id: UUID) -> None:
        model = await self._session.get(CommunityCommentAttachmentModel, attachment_id)
        if model is not None:
            await self._session.delete(model)
