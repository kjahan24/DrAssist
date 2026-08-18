"""`ManageAnswerAttachmentsService` — add/list/remove an answer's own
"Answer Attachments" (this task's own ATTACHMENTS section: "Reuse the
existing File/Document storage architecture. Store references only.").
Not named in this task's own APPLICATION list — the same "add what's
genuinely required" precedent
`app.modules.community_questions.application.services
.manage_question_attachments_service.ManageQuestionAttachmentsService`
establishes for itself. Author-or-moderator authorized, the same rule
`UpdateAnswerService` uses.

`DocumentQueryPort.document_exists` validates `document_id` before
storing the reference; the actual file bytes, upload flow, and storage
backend all remain entirely `app.modules.documents`'s own responsibility.
"""

from uuid import UUID

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_answers.application.dto import (
    AddAnswerAttachmentInput,
    AnswerAttachmentSummaryDTO,
    RemoveAnswerAttachmentInput,
)
from app.modules.community_answers.application.services._authorization import (
    ensure_can_author_action,
)
from app.modules.community_answers.application.services._summary_mappers import (
    answer_attachment_to_summary,
)
from app.modules.community_answers.domain.entities import CommunityAnswerAttachment
from app.modules.community_answers.domain.exceptions import (
    AnswerAttachmentNotFoundError,
    AnswerNotFoundError,
    DocumentNotFoundForAnswerError,
    DuplicateAnswerAttachmentError,
)
from app.modules.community_answers.domain.repositories import (
    CommunityAnswerAttachmentRepository,
    CommunityAnswerRepository,
)
from app.modules.community_answers.domain.value_objects import AnswerId
from app.modules.documents.public.interfaces import DocumentQueryPort
from app.shared.application.unit_of_work import UnitOfWork


class ManageAnswerAttachmentsService:
    def __init__(
        self,
        *,
        answer_attachment_repository: CommunityAnswerAttachmentRepository,
        answer_repository: CommunityAnswerRepository,
        community_query_port: CommunityQueryPort,
        document_query_port: DocumentQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._answer_attachments = answer_attachment_repository
        self._answers = answer_repository
        self._communities = community_query_port
        self._documents = document_query_port
        self._uow = unit_of_work

    async def add_attachment(
        self, input_dto: AddAnswerAttachmentInput
    ) -> AnswerAttachmentSummaryDTO:
        answer = await self._answers.get_by_id(input_dto.answer_id)
        if answer is None:
            raise AnswerNotFoundError(input_dto.answer_id)

        member = await self._communities.get_membership(
            answer.community_id, input_dto.acting_user_id
        )
        ensure_can_author_action(
            member,
            community_id=answer.community_id,
            user_id=input_dto.acting_user_id,
            author_id=answer.author_id,
        )

        if not await self._documents.document_exists(input_dto.document_id):
            raise DocumentNotFoundForAnswerError(input_dto.document_id)

        if await self._answer_attachments.is_assigned(input_dto.answer_id, input_dto.document_id):
            raise DuplicateAnswerAttachmentError(input_dto.answer_id, input_dto.document_id)

        attachment = CommunityAnswerAttachment.create(
            answer_id=AnswerId(input_dto.answer_id), document_id=input_dto.document_id
        )
        await self._answer_attachments.add(attachment)
        self._uow.collect_events(attachment.pull_events())
        await self._uow.commit()

        return answer_attachment_to_summary(attachment)

    async def list_attachments(self, answer_id: UUID) -> list[AnswerAttachmentSummaryDTO]:
        attachments = await self._answer_attachments.list_by_answer(answer_id)
        return [answer_attachment_to_summary(a) for a in attachments]

    async def remove_attachment(self, input_dto: RemoveAnswerAttachmentInput) -> None:
        answer = await self._answers.get_by_id(input_dto.answer_id)
        if answer is None:
            raise AnswerNotFoundError(input_dto.answer_id)

        member = await self._communities.get_membership(
            answer.community_id, input_dto.acting_user_id
        )
        ensure_can_author_action(
            member,
            community_id=answer.community_id,
            user_id=input_dto.acting_user_id,
            author_id=answer.author_id,
        )

        attachment = await self._answer_attachments.get_by_id(input_dto.attachment_id)
        if attachment is None or attachment.answer_id.value != input_dto.answer_id:
            raise AnswerAttachmentNotFoundError(input_dto.attachment_id)

        await self._answer_attachments.remove(input_dto.attachment_id)
        await self._uow.commit()
