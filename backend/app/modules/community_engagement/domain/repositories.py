"""Repository interfaces (ports) for the Community Engagement module.
Concrete implementations live in `infrastructure/repositories.py`; the
application layer depends only on these ABCs.

No repository exposes a status-transition-style "soft delete" — `remove()`
on every one of these five interfaces is a genuine hard delete, matching
each aggregate's own `mark_removed()` — see `entities.py`'s own module
docstring for why votes/saves/follows have no lifecycle worth preserving.

`VoteRepository.count_votes` is the sole source of truth for "Vote
counts"/"Net score" — there is no denormalized counter column on `Vote`
itself or on any content module's own table to keep in sync (and
therefore nothing that could ever drift out of consistency); every count
is computed live from the `votes` table. `SavedContentRepository`/
`TopicFollowerRepository`/`CommunityFollowerRepository`/
`DoctorFollowerRepository` follow the identical "count is a live query,
never a stored field" shape for the same reason — see this task's own
"Do not directly mutate counters without appropriate domain/application
safeguards" DOMAIN rule.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.modules.community_engagement.domain.entities import (
    CommunityFollower,
    DoctorFollower,
    SavedContent,
    TopicFollower,
    Vote,
)
from app.modules.community_engagement.domain.enums import EngagementTargetType, VoteType


class VoteRepository(ABC):
    @abstractmethod
    async def get_by_id(self, vote_id: UUID) -> Vote | None: ...

    @abstractmethod
    async def get_vote(
        self, user_id: UUID, target_type: EngagementTargetType, target_id: UUID
    ) -> Vote | None: ...

    @abstractmethod
    async def count_votes(
        self, target_type: EngagementTargetType, target_id: UUID
    ) -> dict[VoteType, int]:
        """Returns a mapping with exactly the two `VoteType` members as
        keys (zero-filled when a direction has no votes at all) — never
        a sparse dict a caller would need to `.get(..., 0)` around."""
        ...

    @abstractmethod
    async def add(self, vote: Vote) -> None: ...

    @abstractmethod
    async def remove(self, vote_id: UUID) -> None: ...


class SavedContentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, saved_content_id: UUID) -> SavedContent | None: ...

    @abstractmethod
    async def get_saved(
        self, user_id: UUID, target_type: EngagementTargetType, target_id: UUID
    ) -> SavedContent | None: ...

    @abstractmethod
    async def list_by_user(
        self,
        user_id: UUID,
        *,
        target_type: EngagementTargetType | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[Sequence[SavedContent], str | None]: ...

    @abstractmethod
    async def add(self, saved: SavedContent) -> None: ...

    @abstractmethod
    async def remove(self, saved_content_id: UUID) -> None: ...


class TopicFollowerRepository(ABC):
    @abstractmethod
    async def get_by_id(self, topic_follower_id: UUID) -> TopicFollower | None: ...

    @abstractmethod
    async def get_follow(self, user_id: UUID, topic_id: UUID) -> TopicFollower | None: ...

    @abstractmethod
    async def list_followers(
        self, topic_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[TopicFollower], str | None]: ...

    @abstractmethod
    async def list_following(
        self, user_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[TopicFollower], str | None]: ...

    @abstractmethod
    async def count_followers(self, topic_id: UUID) -> int: ...

    @abstractmethod
    async def add(self, follower: TopicFollower) -> None: ...

    @abstractmethod
    async def remove(self, topic_follower_id: UUID) -> None: ...


class CommunityFollowerRepository(ABC):
    @abstractmethod
    async def get_by_id(self, community_follower_id: UUID) -> CommunityFollower | None: ...

    @abstractmethod
    async def get_follow(self, user_id: UUID, community_id: UUID) -> CommunityFollower | None: ...

    @abstractmethod
    async def list_followers(
        self, community_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[CommunityFollower], str | None]: ...

    @abstractmethod
    async def list_following(
        self, user_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[CommunityFollower], str | None]: ...

    @abstractmethod
    async def count_followers(self, community_id: UUID) -> int: ...

    @abstractmethod
    async def add(self, follower: CommunityFollower) -> None: ...

    @abstractmethod
    async def remove(self, community_follower_id: UUID) -> None: ...


class DoctorFollowerRepository(ABC):
    @abstractmethod
    async def get_by_id(self, doctor_follower_id: UUID) -> DoctorFollower | None: ...

    @abstractmethod
    async def get_follow(
        self, follower_user_id: UUID, followed_user_id: UUID
    ) -> DoctorFollower | None: ...

    @abstractmethod
    async def list_followers(
        self, followed_user_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[DoctorFollower], str | None]: ...

    @abstractmethod
    async def list_following(
        self, follower_user_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[DoctorFollower], str | None]: ...

    @abstractmethod
    async def count_followers(self, followed_user_id: UUID) -> int: ...

    @abstractmethod
    async def add(self, follower: DoctorFollower) -> None: ...

    @abstractmethod
    async def remove(self, doctor_follower_id: UUID) -> None: ...
