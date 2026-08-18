"""Concrete SQLAlchemy repository implementations.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern in
`app.modules.community_comments.infrastructure.repositories`.
`remove()` is a genuine `DELETE`, not a status flip — see `entities.py`'s
own module docstring for why none of these five aggregates has anything
worth soft-deleting.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.

Every cursor-paginated `list_*` method here shares the identical
`(created_at, id)` keyset-pagination shape `app.modules.community_comments
.infrastructure.repositories.SqlAlchemyCommunityCommentRepository.browse`
already establishes — descending by `created_at`, `id` as the tiebreak.
"""

import base64
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.query_utils import count_total
from app.modules.community_engagement.domain.entities import (
    CommunityFollower,
    DoctorFollower,
    SavedContent,
    TopicFollower,
    Vote,
)
from app.modules.community_engagement.domain.enums import EngagementTargetType, VoteType
from app.modules.community_engagement.domain.repositories import (
    CommunityFollowerRepository,
    DoctorFollowerRepository,
    SavedContentRepository,
    TopicFollowerRepository,
    VoteRepository,
)
from app.modules.community_engagement.infrastructure.mappers import (
    apply_community_follower_to_model,
    apply_doctor_follower_to_model,
    apply_saved_content_to_model,
    apply_topic_follower_to_model,
    apply_vote_to_model,
    community_follower_to_domain,
    doctor_follower_to_domain,
    saved_content_to_domain,
    topic_follower_to_domain,
    vote_to_domain,
)
from app.modules.community_engagement.infrastructure.models import (
    CommunityFollowerModel,
    DoctorFollowerModel,
    SavedContentModel,
    TopicFollowerModel,
    VoteModel,
)

_CURSOR_SEPARATOR = "|"


def _encode_cursor(created_at: datetime, row_id: UUID) -> str:
    payload = f"{created_at.isoformat()}{_CURSOR_SEPARATOR}{row_id}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    payload = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    created_at_raw, row_id_raw = payload.split(_CURSOR_SEPARATOR, 1)
    return datetime.fromisoformat(created_at_raw), UUID(row_id_raw)


class SqlAlchemyVoteRepository(VoteRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, vote_id: UUID) -> Vote | None:
        model = await self._session.get(VoteModel, vote_id)
        return vote_to_domain(model) if model is not None else None

    async def get_vote(
        self, user_id: UUID, target_type: EngagementTargetType, target_id: UUID
    ) -> Vote | None:
        stmt = select(VoteModel).where(
            VoteModel.user_id == user_id,
            VoteModel.target_type == target_type,
            VoteModel.target_id == target_id,
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return vote_to_domain(model) if model is not None else None

    async def count_votes(
        self, target_type: EngagementTargetType, target_id: UUID
    ) -> dict[VoteType, int]:
        stmt = (
            select(VoteModel.vote_type, func.count())
            .where(VoteModel.target_type == target_type, VoteModel.target_id == target_id)
            .group_by(VoteModel.vote_type)
        )
        rows = (await self._session.execute(stmt)).all()
        counts: dict[VoteType, int] = {VoteType.UPVOTE: 0, VoteType.DOWNVOTE: 0}
        for vote_type, count in rows:
            counts[vote_type] = count
        return counts

    async def add(self, vote: Vote) -> None:
        model = await self._session.get(VoteModel, vote.id)
        if model is None:
            model = VoteModel()
            self._session.add(model)
        apply_vote_to_model(vote, model)

    async def remove(self, vote_id: UUID) -> None:
        model = await self._session.get(VoteModel, vote_id)
        if model is not None:
            await self._session.delete(model)


class SqlAlchemySavedContentRepository(SavedContentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, saved_content_id: UUID) -> SavedContent | None:
        model = await self._session.get(SavedContentModel, saved_content_id)
        return saved_content_to_domain(model) if model is not None else None

    async def get_saved(
        self, user_id: UUID, target_type: EngagementTargetType, target_id: UUID
    ) -> SavedContent | None:
        stmt = select(SavedContentModel).where(
            SavedContentModel.user_id == user_id,
            SavedContentModel.target_type == target_type,
            SavedContentModel.target_id == target_id,
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return saved_content_to_domain(model) if model is not None else None

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        target_type: EngagementTargetType | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[Sequence[SavedContent], str | None]:
        conditions = [SavedContentModel.user_id == user_id]
        if target_type is not None:
            conditions.append(SavedContentModel.target_type == target_type)
        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    SavedContentModel.created_at < cursor_created_at,
                    and_(
                        SavedContentModel.created_at == cursor_created_at,
                        SavedContentModel.id < cursor_id,
                    ),
                )
            )

        stmt = (
            select(SavedContentModel)
            .where(*conditions)
            .order_by(SavedContentModel.created_at.desc(), SavedContentModel.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        has_more = len(rows) > limit
        page = rows[:limit]

        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = _encode_cursor(last.created_at, last.id)

        return [saved_content_to_domain(m) for m in page], next_cursor

    async def add(self, saved: SavedContent) -> None:
        model = await self._session.get(SavedContentModel, saved.id)
        if model is None:
            model = SavedContentModel()
            self._session.add(model)
        apply_saved_content_to_model(saved, model)

    async def remove(self, saved_content_id: UUID) -> None:
        model = await self._session.get(SavedContentModel, saved_content_id)
        if model is not None:
            await self._session.delete(model)


class SqlAlchemyTopicFollowerRepository(TopicFollowerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, topic_follower_id: UUID) -> TopicFollower | None:
        model = await self._session.get(TopicFollowerModel, topic_follower_id)
        return topic_follower_to_domain(model) if model is not None else None

    async def get_follow(self, user_id: UUID, topic_id: UUID) -> TopicFollower | None:
        stmt = select(TopicFollowerModel).where(
            TopicFollowerModel.user_id == user_id, TopicFollowerModel.topic_id == topic_id
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return topic_follower_to_domain(model) if model is not None else None

    async def list_followers(
        self, topic_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[TopicFollower], str | None]:
        conditions = [TopicFollowerModel.topic_id == topic_id]
        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    TopicFollowerModel.created_at < cursor_created_at,
                    and_(
                        TopicFollowerModel.created_at == cursor_created_at,
                        TopicFollowerModel.id < cursor_id,
                    ),
                )
            )
        stmt = (
            select(TopicFollowerModel)
            .where(*conditions)
            .order_by(TopicFollowerModel.created_at.desc(), TopicFollowerModel.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        has_more = len(rows) > limit
        page = rows[:limit]
        next_cursor = (
            _encode_cursor(page[-1].created_at, page[-1].id) if has_more and page else None
        )
        return [topic_follower_to_domain(m) for m in page], next_cursor

    async def list_following(
        self, user_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[TopicFollower], str | None]:
        conditions = [TopicFollowerModel.user_id == user_id]
        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    TopicFollowerModel.created_at < cursor_created_at,
                    and_(
                        TopicFollowerModel.created_at == cursor_created_at,
                        TopicFollowerModel.id < cursor_id,
                    ),
                )
            )
        stmt = (
            select(TopicFollowerModel)
            .where(*conditions)
            .order_by(TopicFollowerModel.created_at.desc(), TopicFollowerModel.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        has_more = len(rows) > limit
        page = rows[:limit]
        next_cursor = (
            _encode_cursor(page[-1].created_at, page[-1].id) if has_more and page else None
        )
        return [topic_follower_to_domain(m) for m in page], next_cursor

    async def count_followers(self, topic_id: UUID) -> int:
        stmt = select(TopicFollowerModel).where(TopicFollowerModel.topic_id == topic_id)
        return await count_total(self._session, stmt)

    async def add(self, follower: TopicFollower) -> None:
        model = await self._session.get(TopicFollowerModel, follower.id)
        if model is None:
            model = TopicFollowerModel()
            self._session.add(model)
        apply_topic_follower_to_model(follower, model)

    async def remove(self, topic_follower_id: UUID) -> None:
        model = await self._session.get(TopicFollowerModel, topic_follower_id)
        if model is not None:
            await self._session.delete(model)


class SqlAlchemyCommunityFollowerRepository(CommunityFollowerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, community_follower_id: UUID) -> CommunityFollower | None:
        model = await self._session.get(CommunityFollowerModel, community_follower_id)
        return community_follower_to_domain(model) if model is not None else None

    async def get_follow(self, user_id: UUID, community_id: UUID) -> CommunityFollower | None:
        stmt = select(CommunityFollowerModel).where(
            CommunityFollowerModel.user_id == user_id,
            CommunityFollowerModel.community_id == community_id,
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return community_follower_to_domain(model) if model is not None else None

    async def list_followers(
        self, community_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[CommunityFollower], str | None]:
        conditions = [CommunityFollowerModel.community_id == community_id]
        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    CommunityFollowerModel.created_at < cursor_created_at,
                    and_(
                        CommunityFollowerModel.created_at == cursor_created_at,
                        CommunityFollowerModel.id < cursor_id,
                    ),
                )
            )
        stmt = (
            select(CommunityFollowerModel)
            .where(*conditions)
            .order_by(CommunityFollowerModel.created_at.desc(), CommunityFollowerModel.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        has_more = len(rows) > limit
        page = rows[:limit]
        next_cursor = (
            _encode_cursor(page[-1].created_at, page[-1].id) if has_more and page else None
        )
        return [community_follower_to_domain(m) for m in page], next_cursor

    async def list_following(
        self, user_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[CommunityFollower], str | None]:
        conditions = [CommunityFollowerModel.user_id == user_id]
        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    CommunityFollowerModel.created_at < cursor_created_at,
                    and_(
                        CommunityFollowerModel.created_at == cursor_created_at,
                        CommunityFollowerModel.id < cursor_id,
                    ),
                )
            )
        stmt = (
            select(CommunityFollowerModel)
            .where(*conditions)
            .order_by(CommunityFollowerModel.created_at.desc(), CommunityFollowerModel.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        has_more = len(rows) > limit
        page = rows[:limit]
        next_cursor = (
            _encode_cursor(page[-1].created_at, page[-1].id) if has_more and page else None
        )
        return [community_follower_to_domain(m) for m in page], next_cursor

    async def count_followers(self, community_id: UUID) -> int:
        stmt = select(CommunityFollowerModel).where(
            CommunityFollowerModel.community_id == community_id
        )
        return await count_total(self._session, stmt)

    async def add(self, follower: CommunityFollower) -> None:
        model = await self._session.get(CommunityFollowerModel, follower.id)
        if model is None:
            model = CommunityFollowerModel()
            self._session.add(model)
        apply_community_follower_to_model(follower, model)

    async def remove(self, community_follower_id: UUID) -> None:
        model = await self._session.get(CommunityFollowerModel, community_follower_id)
        if model is not None:
            await self._session.delete(model)


class SqlAlchemyDoctorFollowerRepository(DoctorFollowerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, doctor_follower_id: UUID) -> DoctorFollower | None:
        model = await self._session.get(DoctorFollowerModel, doctor_follower_id)
        return doctor_follower_to_domain(model) if model is not None else None

    async def get_follow(
        self, follower_user_id: UUID, followed_user_id: UUID
    ) -> DoctorFollower | None:
        stmt = select(DoctorFollowerModel).where(
            DoctorFollowerModel.follower_user_id == follower_user_id,
            DoctorFollowerModel.followed_user_id == followed_user_id,
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return doctor_follower_to_domain(model) if model is not None else None

    async def list_followers(
        self, followed_user_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[DoctorFollower], str | None]:
        conditions = [DoctorFollowerModel.followed_user_id == followed_user_id]
        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    DoctorFollowerModel.created_at < cursor_created_at,
                    and_(
                        DoctorFollowerModel.created_at == cursor_created_at,
                        DoctorFollowerModel.id < cursor_id,
                    ),
                )
            )
        stmt = (
            select(DoctorFollowerModel)
            .where(*conditions)
            .order_by(DoctorFollowerModel.created_at.desc(), DoctorFollowerModel.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        has_more = len(rows) > limit
        page = rows[:limit]
        next_cursor = (
            _encode_cursor(page[-1].created_at, page[-1].id) if has_more and page else None
        )
        return [doctor_follower_to_domain(m) for m in page], next_cursor

    async def list_following(
        self, follower_user_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[DoctorFollower], str | None]:
        conditions = [DoctorFollowerModel.follower_user_id == follower_user_id]
        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    DoctorFollowerModel.created_at < cursor_created_at,
                    and_(
                        DoctorFollowerModel.created_at == cursor_created_at,
                        DoctorFollowerModel.id < cursor_id,
                    ),
                )
            )
        stmt = (
            select(DoctorFollowerModel)
            .where(*conditions)
            .order_by(DoctorFollowerModel.created_at.desc(), DoctorFollowerModel.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        has_more = len(rows) > limit
        page = rows[:limit]
        next_cursor = (
            _encode_cursor(page[-1].created_at, page[-1].id) if has_more and page else None
        )
        return [doctor_follower_to_domain(m) for m in page], next_cursor

    async def count_followers(self, followed_user_id: UUID) -> int:
        stmt = select(DoctorFollowerModel).where(
            DoctorFollowerModel.followed_user_id == followed_user_id
        )
        return await count_total(self._session, stmt)

    async def add(self, follower: DoctorFollower) -> None:
        model = await self._session.get(DoctorFollowerModel, follower.id)
        if model is None:
            model = DoctorFollowerModel()
            self._session.add(model)
        apply_doctor_follower_to_model(follower, model)

    async def remove(self, doctor_follower_id: UUID) -> None:
        model = await self._session.get(DoctorFollowerModel, doctor_follower_id)
        if model is not None:
            await self._session.delete(model)
