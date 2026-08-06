"""`ArchivePostService` — moves a `CommunityPost` to `ARCHIVED`. Author-
or-moderator authorized, the same rule `UpdatePostService` uses."""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_posts.application.dto import ArchivePostInput, CommunityPostSummaryDTO
from app.modules.community_posts.application.services._authorization import (
    ensure_can_author_action,
)
from app.modules.community_posts.application.services._summary_mappers import post_to_summary
from app.modules.community_posts.domain.exceptions import PostNotFoundError
from app.modules.community_posts.domain.repositories import CommunityPostRepository
from app.shared.application.unit_of_work import UnitOfWork


class ArchivePostService:
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

    async def execute(self, input_dto: ArchivePostInput) -> CommunityPostSummaryDTO:
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

        post.archive()
        await self._posts.add(post)
        self._uow.collect_events(post.pull_events())
        await self._uow.commit()

        return post_to_summary(post)
