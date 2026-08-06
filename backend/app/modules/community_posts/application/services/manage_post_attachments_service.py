"""`ManagePostAttachmentsService` — add/list/remove a post's own
"Attachment references" (this task's own POST FEATURES/ATTACHMENTS
sections: "Store attachment references only. Reuse the existing File
module. Do NOT build upload/storage."). Not named in this task's own
APPLICATION list — see `ManagePostTopicsService`'s own docstring for the
identical "add what's genuinely required" reasoning and author-or-
moderator authorization rule.

`DocumentQueryPort.document_exists` (this module's first real consumer
of that port — its own docstring explicitly names "Medical Community
attachments" as an expected future dependent) validates `document_id`
before storing the reference; the actual file bytes, upload flow, and
storage backend all remain entirely `app.modules.documents`'s own
responsibility, untouched by this module.
"""

from uuid import UUID

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_posts.application.dto import (
    AddPostAttachmentInput,
    PostAttachmentSummaryDTO,
    RemovePostAttachmentInput,
)
from app.modules.community_posts.application.services._authorization import (
    ensure_can_author_action,
)
from app.modules.community_posts.application.services._summary_mappers import (
    post_attachment_to_summary,
)
from app.modules.community_posts.domain.entities import CommunityPostAttachment
from app.modules.community_posts.domain.exceptions import (
    DocumentNotFoundForPostError,
    DuplicatePostAttachmentError,
    PostAttachmentNotFoundError,
    PostNotFoundError,
)
from app.modules.community_posts.domain.repositories import (
    CommunityPostAttachmentRepository,
    CommunityPostRepository,
)
from app.modules.community_posts.domain.value_objects import PostId
from app.modules.documents.public.interfaces import DocumentQueryPort
from app.shared.application.unit_of_work import UnitOfWork


class ManagePostAttachmentsService:
    def __init__(
        self,
        *,
        post_attachment_repository: CommunityPostAttachmentRepository,
        post_repository: CommunityPostRepository,
        community_query_port: CommunityQueryPort,
        document_query_port: DocumentQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._post_attachments = post_attachment_repository
        self._posts = post_repository
        self._communities = community_query_port
        self._documents = document_query_port
        self._uow = unit_of_work

    async def add_attachment(self, input_dto: AddPostAttachmentInput) -> PostAttachmentSummaryDTO:
        post = await self._posts.get_by_id(input_dto.post_id)
        if post is None:
            raise PostNotFoundError(input_dto.post_id)

        member = await self._communities.get_membership(post.community_id, input_dto.acting_user_id)
        ensure_can_author_action(
            member,
            community_id=post.community_id,
            user_id=input_dto.acting_user_id,
            author_id=post.author_id,
        )

        if not await self._documents.document_exists(input_dto.document_id):
            raise DocumentNotFoundForPostError(input_dto.document_id)

        if await self._post_attachments.is_assigned(input_dto.post_id, input_dto.document_id):
            raise DuplicatePostAttachmentError(input_dto.post_id, input_dto.document_id)

        attachment = CommunityPostAttachment.create(
            post_id=PostId(input_dto.post_id), document_id=input_dto.document_id
        )
        await self._post_attachments.add(attachment)
        self._uow.collect_events(attachment.pull_events())
        await self._uow.commit()

        return post_attachment_to_summary(attachment)

    async def list_attachments(self, post_id: UUID) -> list[PostAttachmentSummaryDTO]:
        attachments = await self._post_attachments.list_by_post(post_id)
        return [post_attachment_to_summary(a) for a in attachments]

    async def remove_attachment(self, input_dto: RemovePostAttachmentInput) -> None:
        post = await self._posts.get_by_id(input_dto.post_id)
        if post is None:
            raise PostNotFoundError(input_dto.post_id)

        member = await self._communities.get_membership(post.community_id, input_dto.acting_user_id)
        ensure_can_author_action(
            member,
            community_id=post.community_id,
            user_id=input_dto.acting_user_id,
            author_id=post.author_id,
        )

        attachment = await self._post_attachments.get_by_id(input_dto.attachment_id)
        if attachment is None or attachment.post_id.value != input_dto.post_id:
            raise PostAttachmentNotFoundError(input_dto.attachment_id)

        await self._post_attachments.remove(input_dto.attachment_id)
        await self._uow.commit()
