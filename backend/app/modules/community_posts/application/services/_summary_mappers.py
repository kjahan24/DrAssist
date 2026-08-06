"""Domain entity -> summary DTO mappers shared by every query-style
service in this package — kept in one place so there is exactly one
mapping per entity, matching the "exactly one definition of each shape"
precedent `app.modules.community.application.services._summary_mappers`/
`app.modules.medical_topics.application.services._summary_mappers`
already establish for themselves.
"""

from app.modules.community_posts.application.dto import (
    CommunityPostSummaryDTO,
    PostAttachmentSummaryDTO,
    PostTagSummaryDTO,
    PostTopicSummaryDTO,
)
from app.modules.community_posts.domain.entities import (
    CommunityPost,
    CommunityPostAttachment,
    CommunityPostTag,
    CommunityPostTopic,
)


def post_to_summary(post: CommunityPost) -> CommunityPostSummaryDTO:
    return CommunityPostSummaryDTO(
        post_id=post.id,
        community_id=post.community_id,
        organization_id=post.organization_id,
        author_id=post.author_id,
        slug=str(post.slug),
        title=str(post.title),
        body=post.body,
        excerpt=str(post.excerpt),
        post_type=post.post_type,
        status=post.status,
        visibility=post.visibility,
        is_anonymous=post.is_anonymous,
        is_pinned=post.is_pinned,
        is_locked=post.is_locked,
        is_featured=post.is_featured,
        read_time_minutes=post.read_time_minutes,
        view_count=post.view_count,
        bookmark_count=post.bookmark_count,
        share_count=post.share_count,
        created_at=post.created_at,
        updated_at=post.updated_at,
        featured_image_document_id=post.featured_image_document_id,
        published_at=post.published_at,
        updated_by=post.updated_by,
    )


def post_topic_to_summary(assignment: CommunityPostTopic) -> PostTopicSummaryDTO:
    return PostTopicSummaryDTO(
        post_topic_id=assignment.id,
        post_id=assignment.post_id.value,
        topic_id=assignment.topic_id,
    )


def post_tag_to_summary(assignment: CommunityPostTag) -> PostTagSummaryDTO:
    return PostTagSummaryDTO(
        post_tag_id=assignment.id, post_id=assignment.post_id.value, tag=assignment.tag
    )


def post_attachment_to_summary(attachment: CommunityPostAttachment) -> PostAttachmentSummaryDTO:
    return PostAttachmentSummaryDTO(
        attachment_id=attachment.id,
        post_id=attachment.post_id.value,
        document_id=attachment.document_id,
    )
