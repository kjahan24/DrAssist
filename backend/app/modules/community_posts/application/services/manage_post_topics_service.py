"""`ManagePostTopicsService` — assign/list/unassign a post's own
"Multiple topics" (this task's own POST FEATURES bullet). Not named in
this task's own APPLICATION list, but required to actually populate the
topic assignments `BrowseTopicFeedService` reads — the same "add what's
genuinely required" precedent this module's own `FeaturePostService`
establishes for itself. Author-or-moderator authorized, the same rule
`UpdatePostService` uses (assigning topics is an editing action).
"""

from uuid import UUID

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_posts.application.dto import (
    AssignPostTopicInput,
    PostTopicSummaryDTO,
    UnassignPostTopicInput,
)
from app.modules.community_posts.application.services._authorization import (
    ensure_can_author_action,
)
from app.modules.community_posts.application.services._summary_mappers import post_topic_to_summary
from app.modules.community_posts.domain.entities import CommunityPostTopic
from app.modules.community_posts.domain.exceptions import (
    DuplicatePostTopicError,
    PostNotFoundError,
    PostTopicNotFoundError,
    TopicNotFoundForPostError,
)
from app.modules.community_posts.domain.repositories import (
    CommunityPostRepository,
    CommunityPostTopicRepository,
)
from app.modules.community_posts.domain.value_objects import PostId
from app.modules.medical_topics.public.interfaces import TopicQueryPort
from app.shared.application.unit_of_work import UnitOfWork


class ManagePostTopicsService:
    def __init__(
        self,
        *,
        post_topic_repository: CommunityPostTopicRepository,
        post_repository: CommunityPostRepository,
        community_query_port: CommunityQueryPort,
        topic_query_port: TopicQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._post_topics = post_topic_repository
        self._posts = post_repository
        self._communities = community_query_port
        self._topics = topic_query_port
        self._uow = unit_of_work

    async def assign_topic(self, input_dto: AssignPostTopicInput) -> PostTopicSummaryDTO:
        post = await self._posts.get_by_id(input_dto.post_id)
        if post is None:
            raise PostNotFoundError(input_dto.post_id)

        member = await self._communities.get_membership(post.community_id, input_dto.acting_user_id)
        ensure_can_author_action(
            member,
            community_id=post.community_id,
            user_id=input_dto.acting_user_id,
            author_id=post.author_id,
        )

        if not await self._topics.topic_exists(input_dto.topic_id):
            raise TopicNotFoundForPostError(input_dto.topic_id)

        if await self._post_topics.is_assigned(input_dto.post_id, input_dto.topic_id):
            raise DuplicatePostTopicError(input_dto.post_id, input_dto.topic_id)

        assignment = CommunityPostTopic.create(
            post_id=PostId(input_dto.post_id), topic_id=input_dto.topic_id
        )
        await self._post_topics.add(assignment)
        self._uow.collect_events(assignment.pull_events())
        await self._uow.commit()

        return post_topic_to_summary(assignment)

    async def list_topics(self, post_id: UUID) -> list[PostTopicSummaryDTO]:
        assignments = await self._post_topics.list_by_post(post_id)
        return [post_topic_to_summary(a) for a in assignments]

    async def unassign_topic(self, input_dto: UnassignPostTopicInput) -> None:
        post = await self._posts.get_by_id(input_dto.post_id)
        if post is None:
            raise PostNotFoundError(input_dto.post_id)

        member = await self._communities.get_membership(post.community_id, input_dto.acting_user_id)
        ensure_can_author_action(
            member,
            community_id=post.community_id,
            user_id=input_dto.acting_user_id,
            author_id=post.author_id,
        )

        assignment = await self._post_topics.get_by_id(input_dto.post_topic_id)
        if assignment is None or assignment.post_id.value != input_dto.post_id:
            raise PostTopicNotFoundError(input_dto.post_topic_id)

        await self._post_topics.remove(input_dto.post_topic_id)
        await self._uow.commit()
