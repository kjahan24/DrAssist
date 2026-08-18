"""Domain events published by Community Engagement module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork`.

Unlike every prior community module, removal here (`VoteRemoved`/
`ContentUnsaved`/`*Unfollowed`) is a genuine hard delete, not a status
transition — see `Vote`/`SavedContent`/`TopicFollower`/
`CommunityFollower`/`DoctorFollower`'s own module docstring for why votes
and follows have no lifecycle worth soft-deleting. The removed-event is
still recorded on the in-memory entity *before* the repository deletes
its row, so the Unit of Work can still collect and publish it after a
successful commit, exactly like every other event in this codebase.
"""

from dataclasses import dataclass
from uuid import UUID

from app.modules.community_engagement.domain.enums import EngagementTargetType, VoteType
from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class VoteCast(DomainEvent):
    vote_id: UUID
    user_id: UUID
    target_type: EngagementTargetType
    target_id: UUID
    vote_type: VoteType


@dataclass(frozen=True, kw_only=True)
class VoteSwitched(DomainEvent):
    vote_id: UUID
    user_id: UUID
    target_type: EngagementTargetType
    target_id: UUID
    previous_vote_type: VoteType
    new_vote_type: VoteType


@dataclass(frozen=True, kw_only=True)
class VoteRemoved(DomainEvent):
    vote_id: UUID
    user_id: UUID
    target_type: EngagementTargetType
    target_id: UUID


@dataclass(frozen=True, kw_only=True)
class ContentSaved(DomainEvent):
    saved_content_id: UUID
    user_id: UUID
    target_type: EngagementTargetType
    target_id: UUID


@dataclass(frozen=True, kw_only=True)
class ContentUnsaved(DomainEvent):
    saved_content_id: UUID
    user_id: UUID
    target_type: EngagementTargetType
    target_id: UUID


@dataclass(frozen=True, kw_only=True)
class TopicFollowed(DomainEvent):
    topic_follower_id: UUID
    user_id: UUID
    topic_id: UUID


@dataclass(frozen=True, kw_only=True)
class TopicUnfollowed(DomainEvent):
    topic_follower_id: UUID
    user_id: UUID
    topic_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityFollowed(DomainEvent):
    community_follower_id: UUID
    user_id: UUID
    community_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityUnfollowed(DomainEvent):
    community_follower_id: UUID
    user_id: UUID
    community_id: UUID


@dataclass(frozen=True, kw_only=True)
class DoctorFollowed(DomainEvent):
    doctor_follower_id: UUID
    follower_user_id: UUID
    followed_user_id: UUID


@dataclass(frozen=True, kw_only=True)
class DoctorUnfollowed(DomainEvent):
    doctor_follower_id: UUID
    follower_user_id: UUID
    followed_user_id: UUID
