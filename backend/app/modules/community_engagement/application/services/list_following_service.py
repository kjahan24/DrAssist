"""`ListFollowingService` — the mirror image of `ListFollowersService`:
"who/what does this user follow" rather than "who follows this
target" — see that service's own docstring for the full "one service,
three dispatch branches" reasoning.
"""

from app.modules.community_engagement.application.dto import FollowerFeedOutput, ListFollowingInput
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


class ListFollowingService:
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

    async def list_following(self, input_dto: ListFollowingInput) -> FollowerFeedOutput:
        if input_dto.follow_target_type is FollowTargetType.TOPIC:
            topic_items, topic_cursor = await self._topic_followers.list_following(
                input_dto.user_id, cursor=input_dto.cursor, limit=input_dto.limit
            )
            return FollowerFeedOutput(
                items=tuple(topic_follower_to_summary(f) for f in topic_items),
                next_cursor=topic_cursor,
            )

        if input_dto.follow_target_type is FollowTargetType.COMMUNITY:
            community_items, community_cursor = await self._community_followers.list_following(
                input_dto.user_id, cursor=input_dto.cursor, limit=input_dto.limit
            )
            return FollowerFeedOutput(
                items=tuple(community_follower_to_summary(f) for f in community_items),
                next_cursor=community_cursor,
            )

        doctor_items, doctor_cursor = await self._doctor_followers.list_following(
            input_dto.user_id, cursor=input_dto.cursor, limit=input_dto.limit
        )
        return FollowerFeedOutput(
            items=tuple(doctor_follower_to_summary(f) for f in doctor_items),
            next_cursor=doctor_cursor,
        )
