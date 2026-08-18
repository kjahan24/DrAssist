"""`ListFollowersService` — this task's own APPLICATION section names
"ListFollowers" once, not "ListTopicFollowers"/"ListCommunityFollowers"/
"ListDoctorFollowers" three times, so this one service dispatches across
all three follower repositories by `FollowTargetType` rather than three
near-duplicate service classes — this task's own "Do not duplicate
voting logic for every content type" instruction, applied here to
follows. Each branch still ultimately calls a distinct, type-specific
repository (`topic_followers`/`community_followers`/`doctor_followers`
are three separate tables — see the migration's own docstring for why),
converged onto the one shared `FollowerSummaryDTO` shape via
`_summary_mappers.py`.
"""

from app.modules.community_engagement.application.dto import FollowerFeedOutput, ListFollowersInput
from app.modules.community_engagement.application.services._summary_mappers import (
    community_follower_to_summary,
    doctor_follower_to_summary,
    topic_follower_to_summary,
)
from app.modules.community_engagement.domain.enums import FollowTargetType
from app.modules.community_engagement.domain.repositories import (
    CommunityFollowerRepository,
    DoctorFollowerRepository,
    TopicFollowerRepository,
)


class ListFollowersService:
    def __init__(
        self,
        *,
        topic_follower_repository: TopicFollowerRepository,
        community_follower_repository: CommunityFollowerRepository,
        doctor_follower_repository: DoctorFollowerRepository,
    ) -> None:
        self._topic_followers = topic_follower_repository
        self._community_followers = community_follower_repository
        self._doctor_followers = doctor_follower_repository

    async def list_followers(self, input_dto: ListFollowersInput) -> FollowerFeedOutput:
        if input_dto.follow_target_type is FollowTargetType.TOPIC:
            topic_items, topic_cursor = await self._topic_followers.list_followers(
                input_dto.target_id, cursor=input_dto.cursor, limit=input_dto.limit
            )
            return FollowerFeedOutput(
                items=tuple(topic_follower_to_summary(f) for f in topic_items),
                next_cursor=topic_cursor,
            )

        if input_dto.follow_target_type is FollowTargetType.COMMUNITY:
            community_items, community_cursor = await self._community_followers.list_followers(
                input_dto.target_id, cursor=input_dto.cursor, limit=input_dto.limit
            )
            return FollowerFeedOutput(
                items=tuple(community_follower_to_summary(f) for f in community_items),
                next_cursor=community_cursor,
            )

        doctor_items, doctor_cursor = await self._doctor_followers.list_followers(
            input_dto.target_id, cursor=input_dto.cursor, limit=input_dto.limit
        )
        return FollowerFeedOutput(
            items=tuple(doctor_follower_to_summary(f) for f in doctor_items),
            next_cursor=doctor_cursor,
        )
