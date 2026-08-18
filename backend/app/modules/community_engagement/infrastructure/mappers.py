"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.

`SavedContentModel`/`TopicFollowerModel`/`CommunityFollowerModel`/
`DoctorFollowerModel` all store only `created_at` (see `models.py`'s own
docstring) — each mapper sets the domain aggregate's required
`updated_at` field equal to `created_at`, since none of those four
aggregates has any mutating method that would ever make the two diverge
(`VoteModel` is the only model with a real `updated_at` column, since
`Vote.switch()` is the one real mutation across all five aggregates).
"""

from app.modules.community_engagement.domain.entities import (
    CommunityFollower,
    DoctorFollower,
    SavedContent,
    TopicFollower,
    Vote,
)
from app.modules.community_engagement.infrastructure.models import (
    CommunityFollowerModel,
    DoctorFollowerModel,
    SavedContentModel,
    TopicFollowerModel,
    VoteModel,
)

# --- Vote --------------------------------------------------------------------------


def vote_to_domain(model: VoteModel) -> Vote:
    return Vote(
        id=model.id,
        user_id=model.user_id,
        organization_id=model.organization_id,
        target_type=model.target_type,
        target_id=model.target_id,
        vote_type=model.vote_type,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_vote_to_model(entity: Vote, model: VoteModel) -> None:
    model.id = entity.id
    model.user_id = entity.user_id
    model.organization_id = entity.organization_id
    model.target_type = entity.target_type
    model.target_id = entity.target_id
    model.vote_type = entity.vote_type


# --- SavedContent -----------------------------------------------------------------


def saved_content_to_domain(model: SavedContentModel) -> SavedContent:
    return SavedContent(
        id=model.id,
        user_id=model.user_id,
        organization_id=model.organization_id,
        target_type=model.target_type,
        target_id=model.target_id,
        created_at=model.created_at,
        updated_at=model.created_at,
    )


def apply_saved_content_to_model(entity: SavedContent, model: SavedContentModel) -> None:
    model.id = entity.id
    model.user_id = entity.user_id
    model.organization_id = entity.organization_id
    model.target_type = entity.target_type
    model.target_id = entity.target_id


# --- TopicFollower ------------------------------------------------------------------


def topic_follower_to_domain(model: TopicFollowerModel) -> TopicFollower:
    return TopicFollower(
        id=model.id,
        user_id=model.user_id,
        organization_id=model.organization_id,
        topic_id=model.topic_id,
        created_at=model.created_at,
        updated_at=model.created_at,
    )


def apply_topic_follower_to_model(entity: TopicFollower, model: TopicFollowerModel) -> None:
    model.id = entity.id
    model.user_id = entity.user_id
    model.organization_id = entity.organization_id
    model.topic_id = entity.topic_id


# --- CommunityFollower --------------------------------------------------------------


def community_follower_to_domain(model: CommunityFollowerModel) -> CommunityFollower:
    return CommunityFollower(
        id=model.id,
        user_id=model.user_id,
        organization_id=model.organization_id,
        community_id=model.community_id,
        created_at=model.created_at,
        updated_at=model.created_at,
    )


def apply_community_follower_to_model(
    entity: CommunityFollower, model: CommunityFollowerModel
) -> None:
    model.id = entity.id
    model.user_id = entity.user_id
    model.organization_id = entity.organization_id
    model.community_id = entity.community_id


# --- DoctorFollower -------------------------------------------------------------------


def doctor_follower_to_domain(model: DoctorFollowerModel) -> DoctorFollower:
    return DoctorFollower(
        id=model.id,
        follower_user_id=model.follower_user_id,
        organization_id=model.organization_id,
        followed_user_id=model.followed_user_id,
        created_at=model.created_at,
        updated_at=model.created_at,
    )


def apply_doctor_follower_to_model(entity: DoctorFollower, model: DoctorFollowerModel) -> None:
    model.id = entity.id
    model.follower_user_id = entity.follower_user_id
    model.organization_id = entity.organization_id
    model.followed_user_id = entity.followed_user_id
