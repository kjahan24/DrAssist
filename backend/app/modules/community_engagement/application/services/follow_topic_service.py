"""`FollowTopicService` — "Follow/Unfollow Medical Topic" (this task's
own FEATURES list). Medical Topics are a platform-wide catalog with no
`organization_id` of their own (`TopicSummaryDTO` has no such field —
see `app.modules.medical_topics.public.dto`), so unlike
`FollowCommunityService`, there is no tenant-match check against the
topic itself; the acting user's own `organization_id` is still stored on
the new `TopicFollower` row (for tenant-scoped bookkeeping of "who in my
organization follows this topic"), just never compared against anything.

Idempotent: following a topic you already follow is a silent no-op —
"Follow/save operations must be idempotent."
"""

from app.modules.community_engagement.application.dto import FollowerSummaryDTO, FollowTopicInput
from app.modules.community_engagement.application.services._summary_mappers import (
    topic_follower_to_summary,
)
from app.modules.community_engagement.domain.entities import TopicFollower
from app.modules.community_engagement.domain.exceptions import TopicNotFoundForFollowError
from app.modules.community_engagement.domain.repositories import TopicFollowerRepository
from app.modules.medical_topics.public.interfaces import TopicQueryPort
from app.shared.application.unit_of_work import UnitOfWork


class FollowTopicService:
    def __init__(
        self,
        *,
        topic_follower_repository: TopicFollowerRepository,
        topic_query_port: TopicQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._followers = topic_follower_repository
        self._topics = topic_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: FollowTopicInput) -> FollowerSummaryDTO:
        if not await self._topics.topic_exists(input_dto.topic_id):
            raise TopicNotFoundForFollowError(input_dto.topic_id)

        existing = await self._followers.get_follow(input_dto.user_id, input_dto.topic_id)
        if existing is not None:
            return topic_follower_to_summary(existing)

        follower = TopicFollower.create(
            user_id=input_dto.user_id,
            organization_id=input_dto.organization_id,
            topic_id=input_dto.topic_id,
        )
        await self._followers.add(follower)
        self._uow.collect_events(follower.pull_events())
        await self._uow.commit()
        return topic_follower_to_summary(follower)
