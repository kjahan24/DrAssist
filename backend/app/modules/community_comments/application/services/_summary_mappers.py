"""Domain entity -> summary DTO mappers shared by every query-style
service in this package — kept in one place so there is exactly one
mapping per entity, matching the precedent
`app.modules.community_answers.application.services._summary_mappers`
already establishes.

`comment_to_summary` is the one mapper in this codebase (alongside
`app.modules.community_answers.application.services._summary_mappers
.answer_to_summary`) that performs real masking rather than a pure 1:1
field copy — see `CommunityCommentSummaryDTO`'s own docstring in
`application/dto.py` for the full "Anonymous Comments"/"Anonymous
Replies" reasoning.
"""

from app.modules.community_comments.application.dto import (
    CommentAttachmentSummaryDTO,
    CommentRevisionSummaryDTO,
    CommunityCommentSummaryDTO,
)
from app.modules.community_comments.domain.entities import (
    CommunityComment,
    CommunityCommentAttachment,
    CommunityCommentRevision,
)


def comment_to_summary(comment: CommunityComment) -> CommunityCommentSummaryDTO:
    return CommunityCommentSummaryDTO(
        comment_id=comment.id,
        target_type=comment.target_type,
        target_id=comment.target_id,
        community_id=comment.community_id,
        organization_id=comment.organization_id,
        topic_id=comment.topic_id,
        body=str(comment.body),
        status=comment.status,
        is_anonymous=comment.is_anonymous,
        root_comment_id=comment.root_comment_id,
        parent_comment_id=comment.parent_comment_id,
        depth=comment.depth,
        revision_number=comment.revision_number,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        author_id=None if comment.is_anonymous else comment.author_id,
        published_at=comment.published_at,
        updated_by=comment.updated_by,
    )


def comment_revision_to_summary(revision: CommunityCommentRevision) -> CommentRevisionSummaryDTO:
    return CommentRevisionSummaryDTO(
        revision_id=revision.id,
        comment_id=revision.comment_id.value,
        revision_number=revision.revision_number,
        previous_body=revision.previous_body,
        author_id=revision.author_id,
        created_at=revision.created_at,
    )


def comment_attachment_to_summary(
    attachment: CommunityCommentAttachment,
) -> CommentAttachmentSummaryDTO:
    return CommentAttachmentSummaryDTO(
        attachment_id=attachment.id,
        comment_id=attachment.comment_id.value,
        document_id=attachment.document_id,
    )
