"""Domain entity -> summary DTO mappers shared by every query-style
service in this package — kept in one place so there is exactly one
mapping per entity, matching the precedent
`app.modules.community_comments.application.services._summary_mappers`
already establishes.

`topic_follower_to_summary`/`community_follower_to_summary`/
`doctor_follower_to_summary` all converge on the one shared
`FollowerSummaryDTO` shape (see that dataclass's own docstring in
`application/dto.py`) — three small mappers rather than one generic
function, since each source entity names its own "which thing is being
followed" field differently (`topic_id`/`community_id`/
`followed_user_id`) and there is no less-duplicative way to bridge that
without reflection, which would be a worse trade.
"""

from app.modules.community_engagement.application.dto import (
    FollowerSummaryDTO,
    SavedContentSummaryDTO,
)
from app.modules.community_engagement.domain.entities import (
    CommunityFollower,
    DoctorFollower,
    SavedContent,
    TopicFollower,
)
from app.modules.community_engagement.domain.enums import FollowTargetType


def saved_content_to_summary(saved: SavedContent) -> SavedContentSummaryDTO:
    return SavedContentSummaryDTO(
        saved_content_id=saved.id,
        user_id=saved.user_id,
        target_type=saved.target_type,
        target_id=saved.target_id,
        created_at=saved.created_at,
    )


def topic_follower_to_summary(follower: TopicFollower) -> FollowerSummaryDTO:
    return FollowerSummaryDTO(
        follow_id=follower.id,
        follow_target_type=FollowTargetType.TOPIC,
        target_id=follower.topic_id,
        user_id=follower.user_id,
        created_at=follower.created_at,
    )


def community_follower_to_summary(follower: CommunityFollower) -> FollowerSummaryDTO:
    return FollowerSummaryDTO(
        follow_id=follower.id,
        follow_target_type=FollowTargetType.COMMUNITY,
        target_id=follower.community_id,
        user_id=follower.user_id,
        created_at=follower.created_at,
    )


def doctor_follower_to_summary(follower: DoctorFollower) -> FollowerSummaryDTO:
    """`.user_id` is always the follower and `.target_id` is always the
    thing/person being followed, for every one of the three follower
    entities this module maps — for `DoctorFollower` specifically that
    means `.follower_user_id` -> `.user_id` and `.followed_user_id` ->
    `.target_id`, the same direction `topic_follower_to_summary`/
    `community_follower_to_summary` already establish (`.user_id` ->
    `.user_id`, `.topic_id`/`.community_id` -> `.target_id`)."""
    return FollowerSummaryDTO(
        follow_id=follower.id,
        follow_target_type=FollowTargetType.DOCTOR,
        target_id=follower.followed_user_id,
        user_id=follower.follower_user_id,
        created_at=follower.created_at,
    )
