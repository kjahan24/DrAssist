"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.

`CommunityAnswerRevisionModel`/`CommunityAnswerAttachmentModel` store
only `created_at` (see `models.py`'s own docstring) — their mappers set
the domain aggregate's required `updated_at` field equal to `created_at`,
since neither of these two aggregates has a single mutating method that
would ever make the two diverge (`CommunityAnswerRevision` in particular
is fully immutable once created).
"""

from app.modules.community_answers.domain.entities import (
    CommunityAnswer,
    CommunityAnswerAttachment,
    CommunityAnswerRevision,
)
from app.modules.community_answers.domain.value_objects import AnswerBody, AnswerId, AnswerSummary
from app.modules.community_answers.infrastructure.models import (
    CommunityAnswerAttachmentModel,
    CommunityAnswerModel,
    CommunityAnswerRevisionModel,
)

# --- CommunityAnswer -----------------------------------------------------------


def community_answer_to_domain(model: CommunityAnswerModel) -> CommunityAnswer:
    return CommunityAnswer(
        id=model.id,
        question_id=model.question_id,
        community_id=model.community_id,
        organization_id=model.organization_id,
        topic_id=model.topic_id,
        author_id=model.author_id,
        body=AnswerBody(model.body),
        summary=AnswerSummary(model.summary),
        status=model.status,
        visibility=model.visibility,
        is_anonymous=model.is_anonymous,
        is_best_answer=model.is_best_answer,
        is_featured=model.is_featured,
        is_pinned=model.is_pinned,
        view_count=model.view_count,
        share_count=model.share_count,
        revision_number=model.revision_number,
        published_at=model.published_at,
        updated_by=model.updated_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_community_answer_to_model(entity: CommunityAnswer, model: CommunityAnswerModel) -> None:
    model.id = entity.id
    model.question_id = entity.question_id
    model.community_id = entity.community_id
    model.organization_id = entity.organization_id
    model.topic_id = entity.topic_id
    model.author_id = entity.author_id
    model.body = str(entity.body)
    model.summary = str(entity.summary)
    model.status = entity.status
    model.visibility = entity.visibility
    model.is_anonymous = entity.is_anonymous
    model.is_best_answer = entity.is_best_answer
    model.is_featured = entity.is_featured
    model.is_pinned = entity.is_pinned
    model.view_count = entity.view_count
    model.share_count = entity.share_count
    model.revision_number = entity.revision_number
    model.published_at = entity.published_at
    model.updated_by = entity.updated_by


# --- CommunityAnswerRevision -----------------------------------------------------


def community_answer_revision_to_domain(
    model: CommunityAnswerRevisionModel,
) -> CommunityAnswerRevision:
    return CommunityAnswerRevision(
        id=model.id,
        answer_id=AnswerId(model.answer_id),
        revision_number=model.revision_number,
        previous_body=model.previous_body,
        author_id=model.author_id,
        created_at=model.created_at,
        updated_at=model.created_at,
    )


def apply_community_answer_revision_to_model(
    entity: CommunityAnswerRevision, model: CommunityAnswerRevisionModel
) -> None:
    model.id = entity.id
    model.answer_id = entity.answer_id.value
    model.revision_number = entity.revision_number
    model.previous_body = entity.previous_body
    model.author_id = entity.author_id


# --- CommunityAnswerAttachment -----------------------------------------------------


def community_answer_attachment_to_domain(
    model: CommunityAnswerAttachmentModel,
) -> CommunityAnswerAttachment:
    return CommunityAnswerAttachment(
        id=model.id,
        answer_id=AnswerId(model.answer_id),
        document_id=model.document_id,
        created_at=model.created_at,
        updated_at=model.created_at,
    )


def apply_community_answer_attachment_to_model(
    entity: CommunityAnswerAttachment, model: CommunityAnswerAttachmentModel
) -> None:
    model.id = entity.id
    model.answer_id = entity.answer_id.value
    model.document_id = entity.document_id
