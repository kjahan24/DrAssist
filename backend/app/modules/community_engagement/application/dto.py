"""Data Transfer Objects for the Community Engagement module's
application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`presentation/schemas.py`, the Pydantic v2 validation boundary).
Use-case input/output DTOs are plain, immutable dataclasses — the same
shape every prior community module's own `application/dto.py`
establishes.

Every listing (`ListSavedContentInput`/`ListFollowersInput`/
`ListFollowingInput`) is cursor-paginated — the same "one flexible
cursor query" precedent `app.modules.community_comments.application.dto`
establishes for its own listings.

`FollowerSummaryDTO` is one shape shared by `TopicFollower`/
`CommunityFollower`/`DoctorFollower` alike (`target_id` means whichever
of `topic_id`/`community_id`/`followed_user_id` applies, discriminated
by `follow_target_type`) — see `_summary_mappers.py`'s own docstring for
why one generic mapper per entity converges on this one output shape
rather than three separate DTOs for what is, from a caller's
perspective, the exact same "who follows/is followed" relationship.

`CastVoteInput`/`SaveContentInput`/`FollowTopicInput`/
`FollowCommunityInput`/`FollowDoctorInput` all carry `organization_id`
explicitly (the acting user's own tenant, supplied by the presentation
layer from `CurrentUser.organization_id`) — voting/saving/following are
deliberately *not* gated behind community membership the way posting
content is (this task's own DOMAIN RULES never asks for that, and
requiring it would block the common "follow a community before joining
it" pattern), so there is no membership lookup to derive tenant
isolation from "for free" the way `app.modules.community_comments
.application.services._authorization.ensure_can_create` does for
Comments. `organization_id` is compared explicitly instead — see
`_target_resolution.py`'s own docstring, and each `Follow*Service`'s
own docstring for the community/user-existence cases. Every `Unfollow*`/
`RemoveVoteInput`/`UnsaveContentInput` skips it entirely: removal never
re-validates the target, only looks up the caller's own existing row by
id — see `entities.py`'s own module docstring for why removal is
unconditionally idempotent.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.community_engagement.domain.enums import (
    EngagementTargetType,
    FollowTargetType,
    VoteType,
)

# --- Voting --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CastVoteInput:
    target_type: EngagementTargetType
    target_id: UUID
    user_id: UUID
    organization_id: UUID
    vote_type: VoteType


@dataclass(frozen=True, slots=True)
class CastVoteOutput:
    vote_id: UUID
    target_type: EngagementTargetType
    target_id: UUID
    vote_type: VoteType


@dataclass(frozen=True, slots=True)
class RemoveVoteInput:
    target_type: EngagementTargetType
    target_id: UUID
    user_id: UUID


@dataclass(frozen=True, slots=True)
class VoteStatusDTO:
    target_type: EngagementTargetType
    target_id: UUID
    vote_type: VoteType | None = None
    """`None` when the acting user has not voted on this target at
    all — distinct from an actual `VoteType` value, never a third
    sentinel."""


@dataclass(frozen=True, slots=True)
class VoteCountsDTO:
    target_type: EngagementTargetType
    target_id: UUID
    upvotes: int
    downvotes: int

    @property
    def net_score(self) -> int:
        return self.upvotes - self.downvotes


# --- Saving --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SaveContentInput:
    target_type: EngagementTargetType
    target_id: UUID
    user_id: UUID
    organization_id: UUID


@dataclass(frozen=True, slots=True)
class SaveContentOutput:
    saved_content_id: UUID
    target_type: EngagementTargetType
    target_id: UUID


@dataclass(frozen=True, slots=True)
class UnsaveContentInput:
    target_type: EngagementTargetType
    target_id: UUID
    user_id: UUID


@dataclass(frozen=True, slots=True)
class SavedContentSummaryDTO:
    saved_content_id: UUID
    user_id: UUID
    target_type: EngagementTargetType
    target_id: UUID
    created_at: datetime

    @property
    def id(self) -> UUID:
        return self.saved_content_id


@dataclass(frozen=True, slots=True)
class ListSavedContentInput:
    organization_id: UUID
    user_id: UUID
    target_type: EngagementTargetType | None = None
    cursor: str | None = None
    limit: int = 20


@dataclass(frozen=True, slots=True)
class SavedContentFeedOutput:
    items: tuple[SavedContentSummaryDTO, ...]
    next_cursor: str | None = None


# --- Following -------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FollowTopicInput:
    user_id: UUID
    organization_id: UUID
    topic_id: UUID


@dataclass(frozen=True, slots=True)
class UnfollowTopicInput:
    user_id: UUID
    topic_id: UUID


@dataclass(frozen=True, slots=True)
class FollowCommunityInput:
    user_id: UUID
    organization_id: UUID
    community_id: UUID


@dataclass(frozen=True, slots=True)
class UnfollowCommunityInput:
    user_id: UUID
    community_id: UUID


@dataclass(frozen=True, slots=True)
class FollowDoctorInput:
    follower_user_id: UUID
    organization_id: UUID
    followed_user_id: UUID


@dataclass(frozen=True, slots=True)
class UnfollowDoctorInput:
    follower_user_id: UUID
    followed_user_id: UUID


@dataclass(frozen=True, slots=True)
class FollowerSummaryDTO:
    follow_id: UUID
    follow_target_type: FollowTargetType
    target_id: UUID
    user_id: UUID
    created_at: datetime

    @property
    def id(self) -> UUID:
        return self.follow_id


@dataclass(frozen=True, slots=True)
class ListFollowersInput:
    follow_target_type: FollowTargetType
    target_id: UUID
    cursor: str | None = None
    limit: int = 20


@dataclass(frozen=True, slots=True)
class ListFollowingInput:
    follow_target_type: FollowTargetType
    user_id: UUID
    cursor: str | None = None
    limit: int = 20


@dataclass(frozen=True, slots=True)
class FollowerFeedOutput:
    items: tuple[FollowerSummaryDTO, ...]
    next_cursor: str | None = None
