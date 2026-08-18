"""`ManageCommentAttachmentsService` — add/list/remove a comment's own
"Comment Attachments" (this task's own ATTACHMENTS section: "Reuse the
existing file/document storage architecture. Store references only.").
Not named in this task's own APPLICATION list — the same "add what's
genuinely required" precedent
`app.modules.community_answers.application.services
.manage_answer_attachments_service.ManageAnswerAttachmentsService`
establishes for itself. Author-or-moderator authorized, the same rule
`UpdateCommentService` uses.

`DocumentQueryPort.document_exists` validates `document_id` before
storing the reference; the actual file bytes, upload flow, and storage
backend all remain entirely `app.modules.documents`'s own responsibility.
"""

from uuid import UUID

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_comments.application.dto import (
    AddCommentAttachmentInput,
    CommentAttachmentSummaryDTO,
    RemoveCommentAttachmentInput,
)
from app.modules.community_comments.application.services._authorization import (
    ensure_can_author_action,
)
from app.modules.community_comments.application.services._summary_mappers import (
    comment_attachment_to_summary,
)
from app.modules.community_comments.domain.entities import CommunityCommentAttachment
from app.modules.community_comments.domain.exceptions import (
    CommentAttachmentNotFoundError,
    CommentNotFoundError,
    DocumentNotFoundForCommentError,
    DuplicateCommentAttachmentError,
)
from app.modules.community_comments.domain.repositories import (
    CommunityCommentAttachmentRepository,
    CommunityCommentRepository,
)
from app.modules.community_comments.domain.value_objects import CommentId
from app.modules.documents.public.interfaces import DocumentQueryPort
from app.shared.application.unit_of_work import UnitOfWork


class ManageCommentAttachmentsService:
    def __init__(
        self,
        *,
        comment_attachment_repository: CommunityCommentAttachmentRepository,
        comment_repository: CommunityCommentRepository,
        community_query_port: CommunityQueryPort,
        document_query_port: DocumentQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._comment_attachments = comment_attachment_repository
        self._comments = comment_repository
        self._communities = community_query_port
        self._documents = document_query_port
        self._uow = unit_of_work

    async def add_attachment(
        self, input_dto: AddCommentAttachmentInput
    ) -> CommentAttachmentSummaryDTO:
        comment = await self._comments.get_by_id(input_dto.comment_id)
        if comment is None:
            raise CommentNotFoundError(input_dto.comment_id)

        member = await self._communities.get_membership(
            comment.community_id, input_dto.acting_user_id
        )
        ensure_can_author_action(
            member,
            community_id=comment.community_id,
            user_id=input_dto.acting_user_id,
            author_id=comment.author_id,
        )

        if not await self._documents.document_exists(input_dto.document_id):
            raise DocumentNotFoundForCommentError(input_dto.document_id)

        if await self._comment_attachments.is_assigned(input_dto.comment_id, input_dto.document_id):
            raise DuplicateCommentAttachmentError(input_dto.comment_id, input_dto.document_id)

        attachment = CommunityCommentAttachment.create(
            comment_id=CommentId(input_dto.comment_id), document_id=input_dto.document_id
        )
        await self._comment_attachments.add(attachment)
        self._uow.collect_events(attachment.pull_events())
        await self._uow.commit()

        return comment_attachment_to_summary(attachment)

    async def list_attachments(self, comment_id: UUID) -> list[CommentAttachmentSummaryDTO]:
        attachments = await self._comment_attachments.list_by_comment(comment_id)
        return [comment_attachment_to_summary(a) for a in attachments]

    async def remove_attachment(self, input_dto: RemoveCommentAttachmentInput) -> None:
        comment = await self._comments.get_by_id(input_dto.comment_id)
        if comment is None:
            raise CommentNotFoundError(input_dto.comment_id)

        member = await self._communities.get_membership(
            comment.community_id, input_dto.acting_user_id
        )
        ensure_can_author_action(
            member,
            community_id=comment.community_id,
            user_id=input_dto.acting_user_id,
            author_id=comment.author_id,
        )

        attachment = await self._comment_attachments.get_by_id(input_dto.attachment_id)
        if attachment is None or attachment.comment_id.value != input_dto.comment_id:
            raise CommentAttachmentNotFoundError(input_dto.attachment_id)

        await self._comment_attachments.remove(input_dto.attachment_id)
        await self._uow.commit()
