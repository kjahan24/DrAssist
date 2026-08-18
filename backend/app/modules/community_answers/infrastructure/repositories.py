"""Concrete SQLAlchemy repository implementations.

Every `add()` below is "upsert": look up the row by id, create it if
missing, then overwrite its mapped columns from the domain entity's
current in-memory state — see the identical pattern in
`app.modules.community_questions.infrastructure.repositories`.

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
from app.modules.community_answers.domain.entities import (
    CommunityAnswer,
    CommunityAnswerAttachment,
    CommunityAnswerRevision,
)
from app.modules.community_answers.domain.enums import AnswerStatus, AnswerVisibility
from app.modules.community_answers.domain.repositories import (
    CommunityAnswerAttachmentRepository,
    CommunityAnswerRepository,
    CommunityAnswerRevisionRepository,
)
from app.modules.community_answers.infrastructure.mappers import (
    apply_community_answer_attachment_to_model,
    apply_community_answer_revision_to_model,
    apply_community_answer_to_model,
    community_answer_attachment_to_domain,
    community_answer_revision_to_domain,
    community_answer_to_domain,
)
from app.modules.community_answers.infrastructure.models import (
    CommunityAnswerAttachmentModel,
    CommunityAnswerModel,
    CommunityAnswerRevisionModel,
)

_CURSOR_SEPARATOR = "|"


def _encode_cursor(published_at: datetime, answer_id: UUID) -> str:
    payload = f"{published_at.isoformat()}{_CURSOR_SEPARATOR}{answer_id}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    payload = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    published_at_raw, answer_id_raw = payload.split(_CURSOR_SEPARATOR, 1)
    return datetime.fromisoformat(published_at_raw), UUID(answer_id_raw)


class SqlAlchemyCommunityAnswerRepository(CommunityAnswerRepository):
    """`browse_feed`'s keyset ("cursor") pagination sorts by
    `(published_at DESC, id DESC)` — the same shape
    `SqlAlchemyCommunityQuestionRepository.browse_feed` already
    establishes, see that class's own docstring for the full reasoning.

    No `remove()` method: see `CommunityAnswerRepository`'s own
    docstring — deletion is the `CommunityAnswer.delete()` status
    transition, persisted through the ordinary `add()` upsert.
    """

    _SORT_COLUMNS: dict[str, InstrumentedAttribute[Any]] = {
        "created_at": CommunityAnswerModel.created_at,
        "updated_at": CommunityAnswerModel.updated_at,
        "published_at": CommunityAnswerModel.published_at,
        "view_count": CommunityAnswerModel.view_count,
        "share_count": CommunityAnswerModel.share_count,
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, answer_id: UUID) -> CommunityAnswer | None:
        model = await self._session.get(CommunityAnswerModel, answer_id)
        return community_answer_to_domain(model) if model is not None else None

    async def get_best_answer_for_question(self, question_id: UUID) -> CommunityAnswer | None:
        stmt = select(CommunityAnswerModel).where(
            CommunityAnswerModel.question_id == question_id,
            CommunityAnswerModel.is_best_answer.is_(True),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return community_answer_to_domain(model) if model is not None else None

    async def search(
        self,
        *,
        organization_id: UUID,
        question_id: UUID | None = None,
        community_id: UUID | None = None,
        topic_id: UUID | None = None,
        author_id: UUID | None = None,
        status: Sequence[AnswerStatus] | None = None,
        visibility: Sequence[AnswerVisibility] | None = None,
        best_answer_only: bool = False,
        featured_only: bool = False,
        pinned_only: bool = False,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        query: str | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[CommunityAnswer], int]:
        stmt = select(CommunityAnswerModel).where(
            CommunityAnswerModel.organization_id == organization_id
        )
        if not include_deleted:
            stmt = stmt.where(CommunityAnswerModel.status != AnswerStatus.DELETED)
        stmt = apply_equality(stmt, CommunityAnswerModel.question_id, question_id)
        stmt = apply_equality(stmt, CommunityAnswerModel.community_id, community_id)
        stmt = apply_equality(stmt, CommunityAnswerModel.topic_id, topic_id)
        stmt = apply_equality(stmt, CommunityAnswerModel.author_id, author_id)
        stmt = apply_in_filter(stmt, CommunityAnswerModel.status, status)
        stmt = apply_in_filter(stmt, CommunityAnswerModel.visibility, visibility)
        if best_answer_only:
            stmt = stmt.where(CommunityAnswerModel.is_best_answer.is_(True))
        if featured_only:
            stmt = stmt.where(CommunityAnswerModel.is_featured.is_(True))
        if pinned_only:
            stmt = stmt.where(CommunityAnswerModel.is_pinned.is_(True))
        stmt = apply_date_range(
            stmt, CommunityAnswerModel.created_at, start=created_from, end=created_to
        )
        stmt = apply_combined_text_search(
            stmt,
            full_text_columns=[CommunityAnswerModel.body, CommunityAnswerModel.summary],
            term=query,
        )

        total = await count_total(self._session, stmt)

        column = self._SORT_COLUMNS.get(sort_by, CommunityAnswerModel.created_at)
        ordered_stmt = apply_sort(stmt, column, sort_order)
        paginated_stmt = apply_pagination(ordered_stmt, offset=offset, limit=limit)
        models = (await self._session.execute(paginated_stmt)).scalars().all()
        return [community_answer_to_domain(model) for model in models], total

    async def browse_feed(
        self,
        *,
        organization_id: UUID,
        question_id: UUID | None = None,
        community_id: UUID | None = None,
        author_id: UUID | None = None,
        pinned_first: bool = False,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[Sequence[CommunityAnswer], str | None]:
        base_conditions: list[Any] = [
            CommunityAnswerModel.organization_id == organization_id,
            CommunityAnswerModel.status == AnswerStatus.PUBLISHED,
        ]
        if question_id is not None:
            base_conditions.append(CommunityAnswerModel.question_id == question_id)
        if community_id is not None:
            base_conditions.append(CommunityAnswerModel.community_id == community_id)
        if author_id is not None:
            base_conditions.append(CommunityAnswerModel.author_id == author_id)

        pinned_models: list[CommunityAnswerModel] = []
        if pinned_first and cursor is None:
            pinned_stmt = (
                select(CommunityAnswerModel)
                .where(*base_conditions, CommunityAnswerModel.is_pinned.is_(True))
                .order_by(CommunityAnswerModel.published_at.desc(), CommunityAnswerModel.id.desc())
            )
            pinned_models = list((await self._session.execute(pinned_stmt)).scalars().all())

        remaining = limit - len(pinned_models)
        regular_models: list[CommunityAnswerModel] = []
        regular_has_more = False
        if remaining > 0:
            regular_conditions = list(base_conditions)
            if pinned_first:
                regular_conditions.append(CommunityAnswerModel.is_pinned.is_(False))
            if cursor is not None:
                cursor_published_at, cursor_id = _decode_cursor(cursor)
                regular_conditions.append(
                    or_(
                        CommunityAnswerModel.published_at < cursor_published_at,
                        and_(
                            CommunityAnswerModel.published_at == cursor_published_at,
                            CommunityAnswerModel.id < cursor_id,
                        ),
                    )
                )
            regular_stmt = (
                select(CommunityAnswerModel)
                .where(*regular_conditions)
                .order_by(CommunityAnswerModel.published_at.desc(), CommunityAnswerModel.id.desc())
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

        return [community_answer_to_domain(model) for model in page_models], next_cursor

    async def add(self, answer: CommunityAnswer) -> None:
        model = await self._session.get(CommunityAnswerModel, answer.id)
        if model is None:
            model = CommunityAnswerModel()
            self._session.add(model)
        apply_community_answer_to_model(answer, model)


class SqlAlchemyCommunityAnswerRevisionRepository(CommunityAnswerRevisionRepository):
    """No `remove()` method — see `CommunityAnswerRevisionRepository`'s
    own docstring: revision history is immutable."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, revision_id: UUID) -> CommunityAnswerRevision | None:
        model = await self._session.get(CommunityAnswerRevisionModel, revision_id)
        return community_answer_revision_to_domain(model) if model is not None else None

    async def list_by_answer(
        self, answer_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[CommunityAnswerRevision]:
        stmt = (
            select(CommunityAnswerRevisionModel)
            .where(CommunityAnswerRevisionModel.answer_id == answer_id)
            .order_by(CommunityAnswerRevisionModel.revision_number.desc())
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_answer_revision_to_domain(model) for model in models]

    async def add(self, revision: CommunityAnswerRevision) -> None:
        model = await self._session.get(CommunityAnswerRevisionModel, revision.id)
        if model is None:
            model = CommunityAnswerRevisionModel()
            self._session.add(model)
        apply_community_answer_revision_to_model(revision, model)


class SqlAlchemyCommunityAnswerAttachmentRepository(CommunityAnswerAttachmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, attachment_id: UUID) -> CommunityAnswerAttachment | None:
        model = await self._session.get(CommunityAnswerAttachmentModel, attachment_id)
        return community_answer_attachment_to_domain(model) if model is not None else None

    async def list_by_answer(self, answer_id: UUID) -> list[CommunityAnswerAttachment]:
        stmt = select(CommunityAnswerAttachmentModel).where(
            CommunityAnswerAttachmentModel.answer_id == answer_id
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [community_answer_attachment_to_domain(model) for model in models]

    async def is_assigned(self, answer_id: UUID, document_id: UUID) -> bool:
        stmt = select(CommunityAnswerAttachmentModel).where(
            CommunityAnswerAttachmentModel.answer_id == answer_id,
            CommunityAnswerAttachmentModel.document_id == document_id,
        )
        total = await count_total(self._session, stmt)
        return total > 0

    async def add(self, attachment: CommunityAnswerAttachment) -> None:
        model = await self._session.get(CommunityAnswerAttachmentModel, attachment.id)
        if model is None:
            model = CommunityAnswerAttachmentModel()
            self._session.add(model)
        apply_community_answer_attachment_to_model(attachment, model)

    async def remove(self, attachment_id: UUID) -> None:
        model = await self._session.get(CommunityAnswerAttachmentModel, attachment_id)
        if model is not None:
            await self._session.delete(model)
