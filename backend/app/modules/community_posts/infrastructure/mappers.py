"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.

`CommunityPostTopicModel`/`CommunityPostTagModel`/
`CommunityPostAttachmentModel` store only `created_at` (see `models.py`'s
own docstring) — their mappers set the domain aggregate's required
`updated_at` field equal to `created_at`, since none of these three
aggregates has a single mutating method that would ever make the two
diverge.
"""

from app.modules.community_posts.domain.entities import (
    CommunityPost,
    CommunityPostAttachment,
    CommunityPostTag,
    CommunityPostTopic,
)
from app.modules.community_posts.domain.value_objects import (
    PostExcerpt,
    PostId,
    PostSlug,
    PostTitle,
)
from app.modules.community_posts.infrastructure.models import (
    CommunityPostAttachmentModel,
    CommunityPostModel,
    CommunityPostTagModel,
    CommunityPostTopicModel,
)

# --- CommunityPost -----------------------------------------------------------------


def community_post_to_domain(model: CommunityPostModel) -> CommunityPost:
    return CommunityPost(
        id=model.id,
        community_id=model.community_id,
        organization_id=model.organization_id,
        author_id=model.author_id,
        slug=PostSlug(model.slug),
        title=PostTitle(model.title),
        body=model.body,
        excerpt=PostExcerpt(model.excerpt),
        post_type=model.post_type,
        status=model.status,
        visibility=model.visibility,
        is_anonymous=model.is_anonymous,
        is_pinned=model.is_pinned,
        is_locked=model.is_locked,
        is_featured=model.is_featured,
        featured_image_document_id=model.featured_image_document_id,
        read_time_minutes=model.read_time_minutes,
        view_count=model.view_count,
        bookmark_count=model.bookmark_count,
        share_count=model.share_count,
        published_at=model.published_at,
        updated_by=model.updated_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_community_post_to_model(entity: CommunityPost, model: CommunityPostModel) -> None:
    model.id = entity.id
    model.community_id = entity.community_id
    model.organization_id = entity.organization_id
    model.author_id = entity.author_id
    model.slug = str(entity.slug)
    model.title = str(entity.title)
    model.body = entity.body
    model.excerpt = str(entity.excerpt)
    model.post_type = entity.post_type
    model.status = entity.status
    model.visibility = entity.visibility
    model.is_anonymous = entity.is_anonymous
    model.is_pinned = entity.is_pinned
    model.is_locked = entity.is_locked
    model.is_featured = entity.is_featured
    model.featured_image_document_id = entity.featured_image_document_id
    model.read_time_minutes = entity.read_time_minutes
    model.view_count = entity.view_count
    model.bookmark_count = entity.bookmark_count
    model.share_count = entity.share_count
    model.published_at = entity.published_at
    model.updated_by = entity.updated_by


# --- CommunityPostTopic -------------------------------------------------------------


def community_post_topic_to_domain(model: CommunityPostTopicModel) -> CommunityPostTopic:
    return CommunityPostTopic(
        id=model.id,
        post_id=PostId(model.post_id),
        topic_id=model.topic_id,
        created_at=model.created_at,
        updated_at=model.created_at,
    )


def apply_community_post_topic_to_model(
    entity: CommunityPostTopic, model: CommunityPostTopicModel
) -> None:
    model.id = entity.id
    model.post_id = entity.post_id.value
    model.topic_id = entity.topic_id


# --- CommunityPostTag ----------------------------------------------------------------


def community_post_tag_to_domain(model: CommunityPostTagModel) -> CommunityPostTag:
    return CommunityPostTag(
        id=model.id,
        post_id=PostId(model.post_id),
        tag=model.tag,
        created_at=model.created_at,
        updated_at=model.created_at,
    )


def apply_community_post_tag_to_model(
    entity: CommunityPostTag, model: CommunityPostTagModel
) -> None:
    model.id = entity.id
    model.post_id = entity.post_id.value
    model.tag = entity.tag


# --- CommunityPostAttachment -----------------------------------------------------------


def community_post_attachment_to_domain(
    model: CommunityPostAttachmentModel,
) -> CommunityPostAttachment:
    return CommunityPostAttachment(
        id=model.id,
        post_id=PostId(model.post_id),
        document_id=model.document_id,
        created_at=model.created_at,
        updated_at=model.created_at,
    )


def apply_community_post_attachment_to_model(
    entity: CommunityPostAttachment, model: CommunityPostAttachmentModel
) -> None:
    model.id = entity.id
    model.post_id = entity.post_id.value
    model.document_id = entity.document_id
