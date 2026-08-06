"""`GetTopicService`/`ListTopicsService`/`TopicFollowerQueryService`/
`TopicSpecialtyQueryService` — read-only query services, the same shape
`app.modules.community.application.services.community_query_service`
establishes for its own `GetCommunityService`/`ListCommunitiesService`/
`CommunityMembershipQueryService`/`CommunityCategoryQueryService` (plain
classes, no `UnitOfWork`, no domain events — reads never mutate).

`TopicFollowerQueryService` backs this task's own "Topic followers"
feature (list/count/is-following), the same "no separate entity, just a
repository/query-service method" shape
`CommunityMembershipQueryService.list_moderators` already establishes for
Community's analogous "Community moderators" feature.
"""

from uuid import UUID

from app.modules.medical_topics.application.dto import (
    ListTopicsInput,
    ListTopicsOutput,
    TopicFollowerSummaryDTO,
    TopicSpecialtySummaryDTO,
    TopicSummaryDTO,
)
from app.modules.medical_topics.application.services._summary_mappers import (
    follower_to_summary,
    specialty_to_summary,
    topic_to_summary,
)
from app.modules.medical_topics.domain.repositories import (
    MedicalTopicFollowerRepository,
    MedicalTopicRepository,
    TopicSpecialtyRepository,
)


class GetTopicService:
    def __init__(self, *, topic_repository: MedicalTopicRepository) -> None:
        self._topics = topic_repository

    async def get_by_id(self, topic_id: UUID) -> TopicSummaryDTO | None:
        topic = await self._topics.get_by_id(topic_id)
        return topic_to_summary(topic) if topic is not None else None

    async def get_by_slug(self, slug: str) -> TopicSummaryDTO | None:
        topic = await self._topics.get_by_slug(slug)
        return topic_to_summary(topic) if topic is not None else None


class ListTopicsService:
    def __init__(self, *, topic_repository: MedicalTopicRepository) -> None:
        self._topics = topic_repository

    async def list_topics(self, input_dto: ListTopicsInput) -> ListTopicsOutput:
        topics, total = await self._topics.search(
            query=input_dto.query,
            status=input_dto.status,
            visibility=input_dto.visibility,
            specialty_id=input_dto.specialty_id,
            parent_id=input_dto.parent_id,
            include_deleted=input_dto.include_deleted,
            sort_by=input_dto.sort_by,
            sort_order=input_dto.sort_order,  # type: ignore[arg-type]
            offset=input_dto.offset,
            limit=input_dto.limit,
        )
        return ListTopicsOutput(items=tuple(topic_to_summary(t) for t in topics), total=total)

    async def list_children(
        self, parent_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[TopicSummaryDTO]:
        children = await self._topics.list_children(parent_id, offset=offset, limit=limit)
        return [topic_to_summary(c) for c in children]


class TopicFollowerQueryService:
    def __init__(self, *, follower_repository: MedicalTopicFollowerRepository) -> None:
        self._followers = follower_repository

    async def list_followers(
        self, topic_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[TopicFollowerSummaryDTO]:
        followers = await self._followers.list_by_topic(topic_id, offset=offset, limit=limit)
        return [follower_to_summary(f) for f in followers]

    async def count_followers(self, topic_id: UUID) -> int:
        return await self._followers.count_by_topic(topic_id)

    async def is_following(self, topic_id: UUID, user_id: UUID) -> bool:
        follower = await self._followers.get_by_topic_and_user(topic_id, user_id)
        return follower is not None


class TopicSpecialtyQueryService:
    def __init__(self, *, specialty_repository: TopicSpecialtyRepository) -> None:
        self._specialties = specialty_repository

    async def list_active(
        self, *, offset: int = 0, limit: int = 100
    ) -> list[TopicSpecialtySummaryDTO]:
        specialties = await self._specialties.list_active(offset=offset, limit=limit)
        return [specialty_to_summary(s) for s in specialties]
