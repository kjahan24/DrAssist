"""`UpdatePostService` — the author (or a community moderator/admin) may
edit a post's own content — see `_authorization.ensure_can_author_action`
for the exact rule."""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_posts.application.dto import UpdatePostInput, UpdatePostOutput
from app.modules.community_posts.application.services._authorization import (
    ensure_can_author_action,
)
from app.modules.community_posts.domain.exceptions import PostNotFoundError
from app.modules.community_posts.domain.repositories import CommunityPostRepository
from app.modules.community_posts.domain.value_objects import PostExcerpt, PostTitle
from app.shared.application.unit_of_work import UnitOfWork


class UpdatePostService:
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

    async def execute(self, input_dto: UpdatePostInput) -> UpdatePostOutput:
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

        post.update_content(
            title=PostTitle(input_dto.title) if input_dto.title is not None else None,
            body=input_dto.body,
            excerpt=PostExcerpt(input_dto.excerpt) if input_dto.excerpt is not None else None,
            regenerate_excerpt=input_dto.regenerate_excerpt,
            post_type=input_dto.post_type,
            visibility=input_dto.visibility,
            is_anonymous=input_dto.is_anonymous,
            featured_image_document_id=input_dto.featured_image_document_id,
            clear_featured_image=input_dto.clear_featured_image,
            updated_by=input_dto.acting_user_id,
        )

        await self._posts.add(post)
        self._uow.collect_events(post.pull_events())
        await self._uow.commit()

        return UpdatePostOutput(
            post_id=post.id, title=str(post.title), status=post.status, visibility=post.visibility
        )
