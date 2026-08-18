"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.

`CommunityCommentRevisionModel`/`CommunityCommentAttachmentModel` store
only `created_at` (see `models.py`'s own docstring) — their mappers set
the domain aggregate's required `updated_at` field equal to `created_at`,
since neither of these two aggregates has a single mutating method that
would ever make the two diverge (`CommunityCommentRevision` in particular
is fully immutable once created).
"""

from app.modules.community_comments.domain.entities import (
    CommunityComment,
    CommunityCommentAttachment,
    CommunityCommentRevision,
)
from app.modules.community_comments.domain.value_objects import CommentBody, CommentId
from app.modules.community_comments.infrastructure.models import (
    CommunityCommentAttachmentModel,
    CommunityCommentModel,
    CommunityCommentRevisionModel,
)

# --- CommunityComment -----------------------------------------------------------


def community_comment_to_domain(model: CommunityCommentModel) -> CommunityComment:
    return CommunityComment(
        id=model.id,
        target_type=model.target_type,
        target_id=model.target_id,
        community_id=model.community_id,
        organization_id=model.organization_id,
        topic_id=model.topic_id,
        author_id=model.author_id,
        body=CommentBody(model.body),
        parent_comment_id=model.parent_comment_id,
        root_comment_id=model.root_comment_id,
        depth=model.depth,
        status=model.status,
        is_anonymous=model.is_anonymous,
        revision_number=model.revision_number,
        published_at=model.published_at,
        updated_by=model.updated_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_community_comment_to_model(
    entity: CommunityComment, model: CommunityCommentModel
) -> None:
    model.id = entity.id
    model.target_type = entity.target_type
    model.target_id = entity.target_id
    model.community_id = entity.community_id
    model.organization_id = entity.organization_id
    model.topic_id = entity.topic_id
    model.author_id = entity.author_id
    model.body = str(entity.body)
    model.parent_comment_id = entity.parent_comment_id
    model.root_comment_id = entity.root_comment_id
    model.depth = entity.depth
    model.status = entity.status
    model.is_anonymous = entity.is_anonymous
    model.revision_number = entity.revision_number
    model.published_at = entity.published_at
    model.updated_by = entity.updated_by


# --- CommunityCommentRevision -----------------------------------------------------


def community_comment_revision_to_domain(
    model: CommunityCommentRevisionModel,
) -> CommunityCommentRevision:
    return CommunityCommentRevision(
        id=model.id,
        comment_id=CommentId(model.comment_id),
        revision_number=model.revision_number,
        previous_body=model.previous_body,
        author_id=model.author_id,
        created_at=model.created_at,
        updated_at=model.created_at,
    )


def apply_community_comment_revision_to_model(
    entity: CommunityCommentRevision, model: CommunityCommentRevisionModel
) -> None:
    model.id = entity.id
    model.comment_id = entity.comment_id.value
    model.revision_number = entity.revision_number
    model.previous_body = entity.previous_body
    model.author_id = entity.author_id


# --- CommunityCommentAttachment -----------------------------------------------------


def community_comment_attachment_to_domain(
    model: CommunityCommentAttachmentModel,
) -> CommunityCommentAttachment:
    return CommunityCommentAttachment(
        id=model.id,
        comment_id=CommentId(model.comment_id),
        document_id=model.document_id,
        created_at=model.created_at,
        updated_at=model.created_at,
    )


def apply_community_comment_attachment_to_model(
    entity: CommunityCommentAttachment, model: CommunityCommentAttachmentModel
) -> None:
    model.id = entity.id
    model.comment_id = entity.comment_id.value
    model.document_id = entity.document_id
