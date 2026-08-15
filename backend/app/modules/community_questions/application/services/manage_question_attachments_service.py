"""`ManageQuestionAttachmentsService` — add/list/remove a question's own
"Attachment references" (this task's own ATTACHMENTS section: "Reuse
existing File module. Store attachment references only."). Not named in
this task's own APPLICATION list — see `ManageQuestionTopicsService`'s
own docstring for the identical "add what's genuinely required"
reasoning and author-or-moderator authorization rule.

`DocumentQueryPort.document_exists` validates `document_id` before
storing the reference; the actual file bytes, upload flow, and storage
backend all remain entirely `app.modules.documents`'s own responsibility
— mirrors `app.modules.community_posts.application.services
.manage_post_attachments_service.ManagePostAttachmentsService` exactly.
"""

from uuid import UUID

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_questions.application.dto import (
    AddQuestionAttachmentInput,
    QuestionAttachmentSummaryDTO,
    RemoveQuestionAttachmentInput,
)
from app.modules.community_questions.application.services._authorization import (
    ensure_can_author_action,
)
from app.modules.community_questions.application.services._summary_mappers import (
    question_attachment_to_summary,
)
from app.modules.community_questions.domain.entities import CommunityQuestionAttachment
from app.modules.community_questions.domain.exceptions import (
    DocumentNotFoundForQuestionError,
    DuplicateQuestionAttachmentError,
    QuestionAttachmentNotFoundError,
    QuestionNotFoundError,
)
from app.modules.community_questions.domain.repositories import (
    CommunityQuestionAttachmentRepository,
    CommunityQuestionRepository,
)
from app.modules.community_questions.domain.value_objects import QuestionId
from app.modules.documents.public.interfaces import DocumentQueryPort
from app.shared.application.unit_of_work import UnitOfWork


class ManageQuestionAttachmentsService:
    def __init__(
        self,
        *,
        question_attachment_repository: CommunityQuestionAttachmentRepository,
        question_repository: CommunityQuestionRepository,
        community_query_port: CommunityQueryPort,
        document_query_port: DocumentQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._question_attachments = question_attachment_repository
        self._questions = question_repository
        self._communities = community_query_port
        self._documents = document_query_port
        self._uow = unit_of_work

    async def add_attachment(
        self, input_dto: AddQuestionAttachmentInput
    ) -> QuestionAttachmentSummaryDTO:
        question = await self._questions.get_by_id(input_dto.question_id)
        if question is None:
            raise QuestionNotFoundError(input_dto.question_id)

        member = await self._communities.get_membership(
            question.community_id, input_dto.acting_user_id
        )
        ensure_can_author_action(
            member,
            community_id=question.community_id,
            user_id=input_dto.acting_user_id,
            author_id=question.author_id,
        )

        if not await self._documents.document_exists(input_dto.document_id):
            raise DocumentNotFoundForQuestionError(input_dto.document_id)

        if await self._question_attachments.is_assigned(
            input_dto.question_id, input_dto.document_id
        ):
            raise DuplicateQuestionAttachmentError(input_dto.question_id, input_dto.document_id)

        attachment = CommunityQuestionAttachment.create(
            question_id=QuestionId(input_dto.question_id), document_id=input_dto.document_id
        )
        await self._question_attachments.add(attachment)
        self._uow.collect_events(attachment.pull_events())
        await self._uow.commit()

        return question_attachment_to_summary(attachment)

    async def list_attachments(self, question_id: UUID) -> list[QuestionAttachmentSummaryDTO]:
        attachments = await self._question_attachments.list_by_question(question_id)
        return [question_attachment_to_summary(a) for a in attachments]

    async def remove_attachment(self, input_dto: RemoveQuestionAttachmentInput) -> None:
        question = await self._questions.get_by_id(input_dto.question_id)
        if question is None:
            raise QuestionNotFoundError(input_dto.question_id)

        member = await self._communities.get_membership(
            question.community_id, input_dto.acting_user_id
        )
        ensure_can_author_action(
            member,
            community_id=question.community_id,
            user_id=input_dto.acting_user_id,
            author_id=question.author_id,
        )

        attachment = await self._question_attachments.get_by_id(input_dto.attachment_id)
        if attachment is None or attachment.question_id.value != input_dto.question_id:
            raise QuestionAttachmentNotFoundError(input_dto.attachment_id)

        await self._question_attachments.remove(input_dto.attachment_id)
        await self._uow.commit()
