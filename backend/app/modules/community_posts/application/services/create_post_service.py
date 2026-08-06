"""`CreatePostService` — provisions a new `CommunityPost`, optionally
assigning its initial topics/tags in the same call (a real "new post"
form submits title/body/topics/tags together, not as N follow-up
requests).

Cross-module reads only — never a private repository import:
`CommunityQueryPort.get_community_summary`/`get_membership` (this
module's first real consumer of that port, see `_authorization.py`'s own
docstring) resolve the post's `organization_id` and validate authorship
membership; `TopicQueryPort.topic_exists` validates each of `topic_ids`.

Slug uniqueness is scoped to `(community_id, slug)` (see `PostSlug`'s own
docstring) — if the caller doesn't supply an explicit slug (or the
title-derived one collides), a numeric suffix is appended and retried,
the same well-known "slugify, then disambiguate on collision" idiom
every blogging/CMS platform uses; this loop needs repository I/O, so it
lives here, not on the (pure) `PostSlug.from_title` classmethod.
"""

from uuid import UUID

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_posts.application.dto import CreatePostInput, CreatePostOutput
from app.modules.community_posts.application.services._authorization import ensure_can_create
from app.modules.community_posts.domain.entities import (
    CommunityPost,
    CommunityPostTag,
    CommunityPostTopic,
)
from app.modules.community_posts.domain.exceptions import (
    CommunityNotFoundForPostError,
    DuplicatePostTagError,
    DuplicatePostTopicError,
    TopicNotFoundForPostError,
)
from app.modules.community_posts.domain.repositories import (
    CommunityPostRepository,
    CommunityPostTagRepository,
    CommunityPostTopicRepository,
)
from app.modules.community_posts.domain.value_objects import (
    PostExcerpt,
    PostId,
    PostSlug,
    PostTitle,
)
from app.modules.medical_topics.public.interfaces import TopicQueryPort
from app.shared.application.unit_of_work import UnitOfWork

_MAX_SLUG_ATTEMPTS = 50


class CreatePostService:
    def __init__(
        self,
        *,
        post_repository: CommunityPostRepository,
        post_topic_repository: CommunityPostTopicRepository,
        post_tag_repository: CommunityPostTagRepository,
        community_query_port: CommunityQueryPort,
        topic_query_port: TopicQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._posts = post_repository
        self._post_topics = post_topic_repository
        self._post_tags = post_tag_repository
        self._communities = community_query_port
        self._topics = topic_query_port
        self._uow = unit_of_work

    async def _resolve_unique_slug(
        self, community_id: UUID, title: str, explicit: str | None
    ) -> PostSlug:
        base = PostSlug(explicit) if explicit is not None else PostSlug.from_title(title)
        candidate = base
        for attempt in range(2, _MAX_SLUG_ATTEMPTS + 2):
            if await self._posts.get_by_slug(community_id, str(candidate)) is None:
                return candidate
            candidate = PostSlug(f"{base}-{attempt}")
        return candidate

    async def execute(self, input_dto: CreatePostInput) -> CreatePostOutput:
        community = await self._communities.get_community_summary(input_dto.community_id)
        if community is None:
            raise CommunityNotFoundForPostError(input_dto.community_id)

        member = await self._communities.get_membership(input_dto.community_id, input_dto.author_id)
        ensure_can_create(member, community_id=input_dto.community_id, user_id=input_dto.author_id)

        for topic_id in input_dto.topic_ids:
            if not await self._topics.topic_exists(topic_id):
                raise TopicNotFoundForPostError(topic_id)

        slug = await self._resolve_unique_slug(
            input_dto.community_id, input_dto.title, input_dto.slug
        )

        post = CommunityPost.create(
            community_id=input_dto.community_id,
            organization_id=community.organization_id,
            author_id=input_dto.author_id,
            title=PostTitle(input_dto.title),
            body=input_dto.body,
            slug=slug,
            excerpt=PostExcerpt(input_dto.excerpt) if input_dto.excerpt is not None else None,
            post_type=input_dto.post_type,
            visibility=input_dto.visibility,
            is_anonymous=input_dto.is_anonymous,
            featured_image_document_id=input_dto.featured_image_document_id,
        )

        seen_topic_ids: set[UUID] = set()
        for topic_id in input_dto.topic_ids:
            if topic_id in seen_topic_ids:
                raise DuplicatePostTopicError(post.id, topic_id)
            seen_topic_ids.add(topic_id)

        seen_tags: set[str] = set()
        for tag in input_dto.tags:
            normalized_tag = tag.strip().lower()
            if normalized_tag in seen_tags:
                raise DuplicatePostTagError(post.id, normalized_tag)
            seen_tags.add(normalized_tag)

        await self._posts.add(post)
        events = list(post.pull_events())

        post_id = PostId(post.id)
        for topic_id in input_dto.topic_ids:
            assignment = CommunityPostTopic.create(post_id=post_id, topic_id=topic_id)
            await self._post_topics.add(assignment)
            events.extend(assignment.pull_events())

        for tag in input_dto.tags:
            tag_assignment = CommunityPostTag.create(post_id=post_id, tag=tag)
            await self._post_tags.add(tag_assignment)
            events.extend(tag_assignment.pull_events())

        self._uow.collect_events(events)
        await self._uow.commit()

        return CreatePostOutput(
            post_id=post.id,
            community_id=post.community_id,
            slug=str(post.slug),
            title=str(post.title),
            status=post.status,
        )
