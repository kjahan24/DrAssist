"""`ManagePostTagsService` — assign/list/unassign a post's own "Multiple
tags" (this task's own POST FEATURES bullet). Not named in this task's
own APPLICATION list — see `ManagePostTopicsService`'s own docstring for
the identical "add what's genuinely required" reasoning and author-or-
moderator authorization rule.

Unlike `app.modules.community.application.services
.manage_community_tags_service.ManageCommunityTagsService` (which
resolves a shared, platform-wide `CommunityTag` row by name), a post tag
here is plain, per-post free text — this task's own DOMAIN section names
only `CommunityPostTag`, no separate platform-tag-vocabulary entity for
posts (see `CommunityPostTag`'s own docstring)."""

from uuid import UUID

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_posts.application.dto import (
    AssignPostTagInput,
    PostTagSummaryDTO,
    UnassignPostTagInput,
)
from app.modules.community_posts.application.services._authorization import (
    ensure_can_author_action,
)
from app.modules.community_posts.application.services._summary_mappers import post_tag_to_summary
from app.modules.community_posts.domain.entities import CommunityPostTag
from app.modules.community_posts.domain.exceptions import (
    DuplicatePostTagError,
    PostNotFoundError,
    PostTagNotFoundError,
)
from app.modules.community_posts.domain.repositories import (
    CommunityPostRepository,
    CommunityPostTagRepository,
)
from app.modules.community_posts.domain.value_objects import PostId
from app.shared.application.unit_of_work import UnitOfWork


class ManagePostTagsService:
    def __init__(
        self,
        *,
        post_tag_repository: CommunityPostTagRepository,
        post_repository: CommunityPostRepository,
        community_query_port: CommunityQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._post_tags = post_tag_repository
        self._posts = post_repository
        self._communities = community_query_port
        self._uow = unit_of_work

    async def assign_tag(self, input_dto: AssignPostTagInput) -> PostTagSummaryDTO:
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

        normalized = input_dto.tag.strip().lower()
        if await self._post_tags.is_assigned(input_dto.post_id, normalized):
            raise DuplicatePostTagError(input_dto.post_id, normalized)

        assignment = CommunityPostTag.create(post_id=PostId(input_dto.post_id), tag=input_dto.tag)
        await self._post_tags.add(assignment)
        self._uow.collect_events(assignment.pull_events())
        await self._uow.commit()

        return post_tag_to_summary(assignment)

    async def list_tags(self, post_id: UUID) -> list[PostTagSummaryDTO]:
        assignments = await self._post_tags.list_by_post(post_id)
        return [post_tag_to_summary(a) for a in assignments]

    async def unassign_tag(self, input_dto: UnassignPostTagInput) -> None:
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

        assignment = await self._post_tags.get_by_id(input_dto.post_tag_id)
        if assignment is None or assignment.post_id.value != input_dto.post_id:
            raise PostTagNotFoundError(input_dto.post_tag_id)

        await self._post_tags.remove(input_dto.post_tag_id)
        await self._uow.commit()
