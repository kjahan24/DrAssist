"""Pydantic v2 response schemas for the Community Engagement module.

No request schemas at all — every mutating endpoint in this module is
addressed entirely by path/query parameters (`target_type`/`target_id`/
`vote_type`, or a path-scoped `topic_id`/`community_id`/`doctor
user_id`), never a JSON body: a vote/save/follow carries no free-text
content of its own to validate, only identifiers and (for votes) one
enum choice, all of which FastAPI/Pydantic already validate as ordinary
typed query parameters — see `router.py`'s own docstring. This mirrors
how every `DELETE` endpoint across this codebase already needs no
request body; this module simply extends that same shape to its `POST`
endpoints too, since they are equally identifier-only.
"""

from datetime import datetime
from uuid import UUID

from app.modules.community_engagement.domain.enums import (
    EngagementTargetType,
    FollowTargetType,
    VoteType,
)
from app.schemas.base import ORJSONModel


class VoteResponse(ORJSONModel):
    vote_id: UUID
    target_type: EngagementTargetType
    target_id: UUID
    vote_type: VoteType


class VoteStatusResponse(ORJSONModel):
    target_type: EngagementTargetType
    target_id: UUID
    vote_type: VoteType | None = None


class VoteCountsResponse(ORJSONModel):
    target_type: EngagementTargetType
    target_id: UUID
    upvotes: int
    downvotes: int
    net_score: int


class SavedContentResponse(ORJSONModel):
    saved_content_id: UUID
    target_type: EngagementTargetType
    target_id: UUID


class SavedContentSummaryResponse(ORJSONModel):
    id: UUID
    user_id: UUID
    target_type: EngagementTargetType
    target_id: UUID
    created_at: datetime


class SavedContentFeedResponse(ORJSONModel):
    items: list[SavedContentSummaryResponse]
    next_cursor: str | None = None


class FollowerResponse(ORJSONModel):
    id: UUID
    follow_target_type: FollowTargetType
    target_id: UUID
    user_id: UUID
    created_at: datetime


class FollowerFeedResponse(ORJSONModel):
    items: list[FollowerResponse]
    next_cursor: str | None = None
