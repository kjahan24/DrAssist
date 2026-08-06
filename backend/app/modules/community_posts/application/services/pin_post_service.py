"""`PinPostService` — moderator-only toggle (see `_authorization
.ensure_is_moderator`'s own docstring for why no author exception
applies here, unlike Update/Delete/Publish/Archive)."""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_posts.application.dto import SetPostPinnedInput
from app.modules.community_posts.application.services._authorization import ensure_is_moderator
from app.modules.community_posts.domain.exceptions import PostNotFoundError
from app.modules.community_posts.domain.repositories import CommunityPostRepository
from app.shared.application.unit_of_work import UnitOfWork


class PinPostService:
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

    async def execute(self, input_dto: SetPostPinnedInput) -> None:
        post = await self._posts.get_by_id(input_dto.post_id)
        if post is None:
            raise PostNotFoundError(input_dto.post_id)

        member = await self._communities.get_membership(post.community_id, input_dto.acting_user_id)
        ensure_is_moderator(
            member, community_id=post.community_id, user_id=input_dto.acting_user_id
        )

        post.set_pinned(input_dto.pinned)
        await self._posts.add(post)
        self._uow.collect_events(post.pull_events())
        await self._uow.commit()
