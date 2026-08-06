"""`FeaturePostService` — moderator-only toggle for `is_featured`. Not
named in this task's own APPLICATION list, but required to make the
"Featured flag" FEATURES bullet an actual, reachable behavior — the same
"add what's genuinely required" precedent
`app.modules.community.application.services.create_community_category_service
.CreateCommunityCategoryService`/`app.modules.medical_topics.application
.services.create_topic_specialty_service.CreateTopicSpecialtyService`
establish for their own, analogous need."""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_posts.application.dto import SetPostFeaturedInput
from app.modules.community_posts.application.services._authorization import ensure_is_moderator
from app.modules.community_posts.domain.exceptions import PostNotFoundError
from app.modules.community_posts.domain.repositories import CommunityPostRepository
from app.shared.application.unit_of_work import UnitOfWork


class FeaturePostService:
    def __init__(
        self,
        *,
        post_repository: CommunityPostRepository,
        community_query_port: CommunityQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._posts = post_repository
        self._communities = community_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: SetPostFeaturedInput) -> None:
        post = await self._posts.get_by_id(input_dto.post_id)
        if post is None:
            raise PostNotFoundError(input_dto.post_id)

        member = await self._communities.get_membership(post.community_id, input_dto.acting_user_id)
        ensure_is_moderator(
            member, community_id=post.community_id, user_id=input_dto.acting_user_id
        )

        post.set_featured(input_dto.featured)
        await self._posts.add(post)
        self._uow.collect_events(post.pull_events())
        await self._uow.commit()
