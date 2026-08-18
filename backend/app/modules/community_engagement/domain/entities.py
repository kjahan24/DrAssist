"""Community Engagement module aggregate roots: `Vote`, `SavedContent`,
`TopicFollower`, `CommunityFollower`, `DoctorFollower`.

Every reference to another aggregate, including cross-module ones
(`target_id` -> CommunityPost/CommunityQuestion/CommunityAnswer/
CommunityComment, `topic_id` -> MedicalTopic, `community_id` ->
Community, `user_id`/`follower_user_id`/`followed_user_id` -> User), is
by ID only, never by object reference — the same rule
`app.modules.community_comments.domain.entities` already follows.
Cross-module ID references are validated by the application layer via
that peer module's own public query port, never by importing across
`domain/` packages.

None of these five aggregates has a `status` field or any lifecycle
worth soft-deleting — a vote/save/follow either currently exists or it
doesn't; there is no draft/archive/audit-trail value in keeping a
"removed" row around the way `CommunityComment.delete()`'s
business-visible status transition has for actual content. Removal here
is therefore a genuine hard delete: each aggregate exposes a
`mark_removed()` method that only records the domain event (so the Unit
of Work can still publish it after a successful commit); the repository
itself performs the actual row deletion — see each `*Repository.remove`'s
own docstring.

`Vote.switch()` is the one real state-transition on any of these five
aggregates — see its own docstring for "Vote switching."
"""

from dataclasses import dataclass
from uuid import UUID

from app.modules.community_engagement.domain.enums import EngagementTargetType, VoteType
from app.modules.community_engagement.domain.events import (
    CommunityFollowed,
    CommunityUnfollowed,
    ContentSaved,
    ContentUnsaved,
    DoctorFollowed,
    DoctorUnfollowed,
    TopicFollowed,
    TopicUnfollowed,
    VoteCast,
    VoteRemoved,
    VoteSwitched,
)
from app.shared.domain.entity import AggregateRoot


@dataclass(kw_only=True, eq=False)
class Vote(AggregateRoot):
    user_id: UUID
    organization_id: UUID
    target_type: EngagementTargetType
    target_id: UUID
    vote_type: VoteType

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        organization_id: UUID,
        target_type: EngagementTargetType,
        target_id: UUID,
        vote_type: VoteType,
    ) -> "Vote":
        vote = cls(
            user_id=user_id,
            organization_id=organization_id,
            target_type=target_type,
            target_id=target_id,
            vote_type=vote_type,
        )
        vote.record_event(
            VoteCast(
                vote_id=vote.id,
                user_id=user_id,
                target_type=target_type,
                target_id=target_id,
                vote_type=vote_type,
            )
        )
        return vote

    def switch(self, new_vote_type: VoteType) -> None:
        """ "Vote switching" (this task's own FEATURES list): flips an
        existing upvote to a downvote or vice versa *in place* — one row
        per `(user_id, target_type, target_id)`, never delete-then-
        recreate, so the unique constraint backing "one active vote per
        user per target" is never even momentarily violated. The caller
        (`CastVoteService`) is responsible for only calling this when
        `new_vote_type` actually differs from the current one — casting
        the *same* direction again is a no-op the service short-circuits
        before ever reaching here, keeping this method's own
        responsibility to "perform a switch," not "decide whether one is
        needed."""
        previous_vote_type = self.vote_type
        self.vote_type = new_vote_type
        self.touch()
        self.record_event(
            VoteSwitched(
                vote_id=self.id,
                user_id=self.user_id,
                target_type=self.target_type,
                target_id=self.target_id,
                previous_vote_type=previous_vote_type,
                new_vote_type=new_vote_type,
            )
        )

    def mark_removed(self) -> None:
        self.record_event(
            VoteRemoved(
                vote_id=self.id,
                user_id=self.user_id,
                target_type=self.target_type,
                target_id=self.target_id,
            )
        )


@dataclass(kw_only=True, eq=False)
class SavedContent(AggregateRoot):
    user_id: UUID
    organization_id: UUID
    target_type: EngagementTargetType
    target_id: UUID

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        organization_id: UUID,
        target_type: EngagementTargetType,
        target_id: UUID,
    ) -> "SavedContent":
        saved = cls(
            user_id=user_id,
            organization_id=organization_id,
            target_type=target_type,
            target_id=target_id,
        )
        saved.record_event(
            ContentSaved(
                saved_content_id=saved.id,
                user_id=user_id,
                target_type=target_type,
                target_id=target_id,
            )
        )
        return saved

    def mark_removed(self) -> None:
        self.record_event(
            ContentUnsaved(
                saved_content_id=self.id,
                user_id=self.user_id,
                target_type=self.target_type,
                target_id=self.target_id,
            )
        )


@dataclass(kw_only=True, eq=False)
class TopicFollower(AggregateRoot):
    user_id: UUID
    organization_id: UUID
    topic_id: UUID

    @classmethod
    def create(cls, *, user_id: UUID, organization_id: UUID, topic_id: UUID) -> "TopicFollower":
        follower = cls(user_id=user_id, organization_id=organization_id, topic_id=topic_id)
        follower.record_event(
            TopicFollowed(topic_follower_id=follower.id, user_id=user_id, topic_id=topic_id)
        )
        return follower

    def mark_removed(self) -> None:
        self.record_event(
            TopicUnfollowed(topic_follower_id=self.id, user_id=self.user_id, topic_id=self.topic_id)
        )


@dataclass(kw_only=True, eq=False)
class CommunityFollower(AggregateRoot):
    user_id: UUID
    organization_id: UUID
    community_id: UUID

    @classmethod
    def create(
        cls, *, user_id: UUID, organization_id: UUID, community_id: UUID
    ) -> "CommunityFollower":
        follower = cls(user_id=user_id, organization_id=organization_id, community_id=community_id)
        follower.record_event(
            CommunityFollowed(
                community_follower_id=follower.id, user_id=user_id, community_id=community_id
            )
        )
        return follower

    def mark_removed(self) -> None:
        self.record_event(
            CommunityUnfollowed(
                community_follower_id=self.id, user_id=self.user_id, community_id=self.community_id
            )
        )


@dataclass(kw_only=True, eq=False)
class DoctorFollower(AggregateRoot):
    """Named `DoctorFollower` (matching this task's own literal
    `doctor_followers` table name) but its `followed_user_id` references
    `users.id`, not a `doctors.id` — every content module in this
    codebase tracks authorship via `author_id -> users.id`, and not
    every content author is necessarily a `Doctor` row (patients,
    moderators, and admins can all post/answer/comment too), so a
    `doctors.id` foreign key would wrongly exclude followable authors
    who aren't doctors. "Follow/Unfollow Doctor/Author" is read as one
    feature — following a specific person, whoever they are — not two."""

    follower_user_id: UUID
    organization_id: UUID
    followed_user_id: UUID

    @classmethod
    def create(
        cls, *, follower_user_id: UUID, organization_id: UUID, followed_user_id: UUID
    ) -> "DoctorFollower":
        follower = cls(
            follower_user_id=follower_user_id,
            organization_id=organization_id,
            followed_user_id=followed_user_id,
        )
        follower.record_event(
            DoctorFollowed(
                doctor_follower_id=follower.id,
                follower_user_id=follower_user_id,
                followed_user_id=followed_user_id,
            )
        )
        return follower

    def mark_removed(self) -> None:
        self.record_event(
            DoctorUnfollowed(
                doctor_follower_id=self.id,
                follower_user_id=self.follower_user_id,
                followed_user_id=self.followed_user_id,
            )
        )
