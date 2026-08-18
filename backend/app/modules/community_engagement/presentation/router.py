"""HTTP routes for the Community Engagement module.

Follows the pattern established in `app.modules.community_comments
.presentation.router`. Every endpoint depends on `CurrentUser`.

No endpoint here takes a JSON request body — see `schemas.py`'s own
docstring for why every mutating action is fully addressed by path/query
parameters instead. There is also no `ensure_same_organization` call
anywhere in this router (unlike every prior module's own single-resource
`GET`/`PATCH`/`DELETE` routes): every service in this module already
enforces tenant isolation itself, either by comparing the resolved
target's own `organization_id` against `CurrentUser.organization_id`
(`CastVoteService`/`SaveContentService`/`FollowCommunityService`/
`FollowDoctorService`) or, for `TopicFollower`, because Medical Topics
are a platform-wide catalog with no `organization_id` of their own to
compare — see `FollowTopicService`'s own docstring.

There is no route-ordering concern to document here (unlike every prior
module's own `/search`-before-`/{id}` note) — this module has no
`/{id}`-shaped route at all; every resource is addressed by
`target_type`+`target_id` (votes/saves) or a path-scoped
`topic_id`/`community_id`/user id (follows), never a bare row id.
"""

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser
from app.modules.community_engagement.application.dto import (
    CastVoteInput,
    FollowCommunityInput,
    FollowDoctorInput,
    FollowTopicInput,
    ListFollowersInput,
    ListFollowingInput,
    ListSavedContentInput,
    RemoveVoteInput,
    SaveContentInput,
    UnfollowCommunityInput,
    UnfollowDoctorInput,
    UnfollowTopicInput,
    UnsaveContentInput,
)
from app.modules.community_engagement.domain.enums import (
    EngagementTargetType,
    FollowTargetType,
    VoteType,
)
from app.modules.community_engagement.presentation.dependencies import (
    CastVoteUseCase,
    FollowCommunityUseCase,
    FollowDoctorUseCase,
    FollowTopicUseCase,
    GetVoteCountsQS,
    GetVoteStatusQS,
    ListFollowersQS,
    ListFollowingQS,
    ListSavedContentQS,
    RemoveVoteUseCase,
    SaveContentUseCase,
    UnfollowCommunityUseCase,
    UnfollowDoctorUseCase,
    UnfollowTopicUseCase,
    UnsaveContentUseCase,
)
from app.modules.community_engagement.presentation.schemas import (
    FollowerFeedResponse,
    FollowerResponse,
    SavedContentFeedResponse,
    SavedContentResponse,
    SavedContentSummaryResponse,
    VoteCountsResponse,
    VoteResponse,
    VoteStatusResponse,
)

router = APIRouter()


@router.get("/health")
async def get_community_engagement_health() -> dict[str, str]:
    return {"status": "ok", "module": "community_engagement"}


# --- Voting --------------------------------------------------------------------------


@router.post("/votes", response_model=VoteResponse)
async def cast_vote(
    use_case: CastVoteUseCase,
    current_user: CurrentUser,
    target_type: EngagementTargetType,
    target_id: UUID,
    vote_type: VoteType,
) -> VoteResponse:
    output = await use_case.execute(
        CastVoteInput(
            target_type=target_type,
            target_id=target_id,
            user_id=current_user.user_id,
            organization_id=current_user.organization_id,
            vote_type=vote_type,
        )
    )
    return VoteResponse.model_validate(output)


@router.delete("/votes", status_code=status.HTTP_204_NO_CONTENT)
async def remove_vote(
    use_case: RemoveVoteUseCase,
    current_user: CurrentUser,
    target_type: EngagementTargetType,
    target_id: UUID,
) -> None:
    await use_case.execute(
        RemoveVoteInput(target_type=target_type, target_id=target_id, user_id=current_user.user_id)
    )


@router.get("/votes/status", response_model=VoteStatusResponse)
async def get_vote_status(
    query_service: GetVoteStatusQS,
    current_user: CurrentUser,
    target_type: EngagementTargetType,
    target_id: UUID,
) -> VoteStatusResponse:
    result = await query_service.get_status(target_type, target_id, user_id=current_user.user_id)
    return VoteStatusResponse.model_validate(result)


@router.get("/votes/counts", response_model=VoteCountsResponse)
async def get_vote_counts(
    query_service: GetVoteCountsQS,
    current_user: CurrentUser,
    target_type: EngagementTargetType,
    target_id: UUID,
) -> VoteCountsResponse:
    result = await query_service.get_counts(target_type, target_id)
    return VoteCountsResponse(
        target_type=result.target_type,
        target_id=result.target_id,
        upvotes=result.upvotes,
        downvotes=result.downvotes,
        net_score=result.net_score,
    )


# --- Saving --------------------------------------------------------------------------


@router.post("/saves", response_model=SavedContentResponse)
async def save_content(
    use_case: SaveContentUseCase,
    current_user: CurrentUser,
    target_type: EngagementTargetType,
    target_id: UUID,
) -> SavedContentResponse:
    output = await use_case.execute(
        SaveContentInput(
            target_type=target_type,
            target_id=target_id,
            user_id=current_user.user_id,
            organization_id=current_user.organization_id,
        )
    )
    return SavedContentResponse.model_validate(output)


@router.delete("/saves", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_content(
    use_case: UnsaveContentUseCase,
    current_user: CurrentUser,
    target_type: EngagementTargetType,
    target_id: UUID,
) -> None:
    await use_case.execute(
        UnsaveContentInput(
            target_type=target_type, target_id=target_id, user_id=current_user.user_id
        )
    )


@router.get("/saves", response_model=SavedContentFeedResponse)
async def list_saved_content(
    query_service: ListSavedContentQS,
    current_user: CurrentUser,
    target_type: EngagementTargetType | None = None,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> SavedContentFeedResponse:
    result = await query_service.list_saved(
        ListSavedContentInput(
            organization_id=current_user.organization_id,
            user_id=current_user.user_id,
            target_type=target_type,
            cursor=cursor,
            limit=limit,
        )
    )
    return SavedContentFeedResponse(
        items=[SavedContentSummaryResponse.model_validate(s) for s in result.items],
        next_cursor=result.next_cursor,
    )


# --- Following: Topic ------------------------------------------------------------------


@router.post("/topics/{topic_id}/follow", response_model=FollowerResponse)
async def follow_topic(
    topic_id: UUID, use_case: FollowTopicUseCase, current_user: CurrentUser
) -> FollowerResponse:
    result = await use_case.execute(
        FollowTopicInput(
            user_id=current_user.user_id,
            organization_id=current_user.organization_id,
            topic_id=topic_id,
        )
    )
    return FollowerResponse.model_validate(result)


@router.delete("/topics/{topic_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_topic(
    topic_id: UUID, use_case: UnfollowTopicUseCase, current_user: CurrentUser
) -> None:
    await use_case.execute(UnfollowTopicInput(user_id=current_user.user_id, topic_id=topic_id))


# --- Following: Community ---------------------------------------------------------------


@router.post("/communities/{community_id}/follow", response_model=FollowerResponse)
async def follow_community(
    community_id: UUID, use_case: FollowCommunityUseCase, current_user: CurrentUser
) -> FollowerResponse:
    result = await use_case.execute(
        FollowCommunityInput(
            user_id=current_user.user_id,
            organization_id=current_user.organization_id,
            community_id=community_id,
        )
    )
    return FollowerResponse.model_validate(result)


@router.delete("/communities/{community_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_community(
    community_id: UUID, use_case: UnfollowCommunityUseCase, current_user: CurrentUser
) -> None:
    await use_case.execute(
        UnfollowCommunityInput(user_id=current_user.user_id, community_id=community_id)
    )


# --- Following: Doctor/Author ------------------------------------------------------------


@router.post("/doctors/{user_id}/follow", response_model=FollowerResponse)
async def follow_doctor(
    user_id: UUID, use_case: FollowDoctorUseCase, current_user: CurrentUser
) -> FollowerResponse:
    result = await use_case.execute(
        FollowDoctorInput(
            follower_user_id=current_user.user_id,
            organization_id=current_user.organization_id,
            followed_user_id=user_id,
        )
    )
    return FollowerResponse.model_validate(result)


@router.delete("/doctors/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_doctor(
    user_id: UUID, use_case: UnfollowDoctorUseCase, current_user: CurrentUser
) -> None:
    await use_case.execute(
        UnfollowDoctorInput(follower_user_id=current_user.user_id, followed_user_id=user_id)
    )


# --- Followers / Following (generic, dispatched by follow_target_type) -----------------


@router.get("/followers", response_model=FollowerFeedResponse)
async def list_followers(
    query_service: ListFollowersQS,
    current_user: CurrentUser,
    follow_target_type: FollowTargetType,
    target_id: UUID,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> FollowerFeedResponse:
    result = await query_service.list_followers(
        ListFollowersInput(
            follow_target_type=follow_target_type,
            target_id=target_id,
            cursor=cursor,
            limit=limit,
        )
    )
    return FollowerFeedResponse(
        items=[FollowerResponse.model_validate(f) for f in result.items],
        next_cursor=result.next_cursor,
    )


@router.get("/following", response_model=FollowerFeedResponse)
async def list_following(
    query_service: ListFollowingQS,
    current_user: CurrentUser,
    follow_target_type: FollowTargetType,
    user_id: UUID | None = None,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> FollowerFeedResponse:
    result = await query_service.list_following(
        ListFollowingInput(
            follow_target_type=follow_target_type,
            user_id=user_id if user_id is not None else current_user.user_id,
            cursor=cursor,
            limit=limit,
        )
    )
    return FollowerFeedResponse(
        items=[FollowerResponse.model_validate(f) for f in result.items],
        next_cursor=result.next_cursor,
    )
