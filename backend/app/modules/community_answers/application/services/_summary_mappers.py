"""Domain entity -> summary DTO mappers shared by every query-style
service in this package — kept in one place so there is exactly one
mapping per entity, matching the precedent
`app.modules.community_questions.application.services._summary_mappers`
already establishes.

`answer_to_summary` is the one mapper in this codebase that performs
real masking rather than a pure 1:1 field copy — see `CommunityAnswerSummaryDTO`'s
own docstring in `application/dto.py` for the full "anonymous identity
must remain hidden through the public API" reasoning.
"""

from app.modules.community_answers.application.dto import (
    AnswerAttachmentSummaryDTO,
    AnswerRevisionSummaryDTO,
    CommunityAnswerSummaryDTO,
)
from app.modules.community_answers.domain.entities import (
    CommunityAnswer,
    CommunityAnswerAttachment,
    CommunityAnswerRevision,
)


def answer_to_summary(answer: CommunityAnswer) -> CommunityAnswerSummaryDTO:
    return CommunityAnswerSummaryDTO(
        answer_id=answer.id,
        question_id=answer.question_id,
        community_id=answer.community_id,
        organization_id=answer.organization_id,
        topic_id=answer.topic_id,
        body=str(answer.body),
        summary=str(answer.summary),
        status=answer.status,
        visibility=answer.visibility,
        is_anonymous=answer.is_anonymous,
        is_best_answer=answer.is_best_answer,
        is_featured=answer.is_featured,
        is_pinned=answer.is_pinned,
        view_count=answer.view_count,
        share_count=answer.share_count,
        revision_number=answer.revision_number,
        created_at=answer.created_at,
        updated_at=answer.updated_at,
        author_id=None if answer.is_anonymous else answer.author_id,
        published_at=answer.published_at,
        updated_by=answer.updated_by,
    )


def answer_revision_to_summary(revision: CommunityAnswerRevision) -> AnswerRevisionSummaryDTO:
    return AnswerRevisionSummaryDTO(
        revision_id=revision.id,
        answer_id=revision.answer_id.value,
        revision_number=revision.revision_number,
        previous_body=revision.previous_body,
        author_id=revision.author_id,
        created_at=revision.created_at,
    )


def answer_attachment_to_summary(
    attachment: CommunityAnswerAttachment,
) -> AnswerAttachmentSummaryDTO:
    return AnswerAttachmentSummaryDTO(
        attachment_id=attachment.id,
        answer_id=attachment.answer_id.value,
        document_id=attachment.document_id,
    )
