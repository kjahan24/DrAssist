"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and services
for this module — every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`get_community_query_port`/`get_post_query_port`/`get_question_query_port`/
`get_answer_query_port`/`get_document_query_port` each call the
respective peer module's own `build_*_facade(session)` composition-root
factory — never construct a facade (or any of its repositories) directly
— the same rule `app.modules.community_answers.presentation.dependencies`
already establishes for itself.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.community.container import build_community_facade
from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_answers.container import build_answer_facade
from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.application.services.archive_comment_service import (
    ArchiveCommentService,
)
from app.modules.community_comments.application.services.comment_query_service import (
    GetCommentService,
)
from app.modules.community_comments.application.services.comment_revision_query_service import (
    CommentRevisionQueryService,
)
from app.modules.community_comments.application.services.create_comment_service import (
    CreateCommentService,
)
from app.modules.community_comments.application.services.create_reply_service import (
    CreateReplyService,
)
from app.modules.community_comments.application.services.delete_comment_service import (
    DeleteCommentService,
)
from app.modules.community_comments.application.services.get_thread_service import (
    GetThreadService,
)
from app.modules.community_comments.application.services.list_comments_service import (
    ListCommentsService,
)
from app.modules.community_comments.application.services.list_replies_service import (
    ListRepliesService,
)
from app.modules.community_comments.application.services.manage_comment_attachments_service import (  # noqa: E501
    ManageCommentAttachmentsService,
)
from app.modules.community_comments.application.services.publish_comment_service import (
    PublishCommentService,
)
from app.modules.community_comments.application.services.restore_comment_service import (
    RestoreCommentService,
)
from app.modules.community_comments.application.services.search_comments_service import (
    SearchCommentsService,
)
from app.modules.community_comments.application.services.update_comment_service import (
    UpdateCommentService,
)
from app.modules.community_comments.domain.repositories import (
    CommunityCommentAttachmentRepository,
    CommunityCommentRepository,
    CommunityCommentRevisionRepository,
)
from app.modules.community_comments.infrastructure.repositories import (
    SqlAlchemyCommunityCommentAttachmentRepository,
    SqlAlchemyCommunityCommentRepository,
    SqlAlchemyCommunityCommentRevisionRepository,
)
from app.modules.community_posts.container import build_post_facade
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.container import build_question_facade
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.modules.documents.container import build_document_facade
from app.modules.documents.public.interfaces import DocumentQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_comment_repository(session: DbSession) -> CommunityCommentRepository:
    return SqlAlchemyCommunityCommentRepository(session)


def get_comment_revision_repository(session: DbSession) -> CommunityCommentRevisionRepository:
    return SqlAlchemyCommunityCommentRevisionRepository(session)


def get_comment_attachment_repository(session: DbSession) -> CommunityCommentAttachmentRepository:
    return SqlAlchemyCommunityCommentAttachmentRepository(session)


def get_community_query_port(session: DbSession) -> CommunityQueryPort:
    return build_community_facade(session)


def get_post_query_port(session: DbSession) -> PostQueryPort:
    return build_post_facade(session)


def get_question_query_port(session: DbSession) -> QuestionQueryPort:
    return build_question_facade(session)


def get_answer_query_port(session: DbSession) -> AnswerQueryPort:
    return build_answer_facade(session)


def get_document_query_port(session: DbSession) -> DocumentQueryPort:
    return build_document_facade(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


CommentRepo = Annotated[CommunityCommentRepository, Depends(get_comment_repository)]
CommentRevisionRepo = Annotated[
    CommunityCommentRevisionRepository, Depends(get_comment_revision_repository)
]
CommentAttachmentRepo = Annotated[
    CommunityCommentAttachmentRepository, Depends(get_comment_attachment_repository)
]
CommunityPort = Annotated[CommunityQueryPort, Depends(get_community_query_port)]
PostPort = Annotated[PostQueryPort, Depends(get_post_query_port)]
QuestionPort = Annotated[QuestionQueryPort, Depends(get_question_query_port)]
AnswerPort = Annotated[AnswerQueryPort, Depends(get_answer_query_port)]
DocumentPort = Annotated[DocumentQueryPort, Depends(get_document_query_port)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]


def get_get_comment_service(
    comment_repository: CommentRepo, community_port: CommunityPort
) -> GetCommentService:
    return GetCommentService(
        comment_repository=comment_repository, community_query_port=community_port
    )


def get_create_comment_service(
    comment_repository: CommentRepo,
    community_port: CommunityPort,
    post_port: PostPort,
    question_port: QuestionPort,
    answer_port: AnswerPort,
    unit_of_work: Uow,
) -> CreateCommentService:
    return CreateCommentService(
        comment_repository=comment_repository,
        community_query_port=community_port,
        post_query_port=post_port,
        question_query_port=question_port,
        answer_query_port=answer_port,
        unit_of_work=unit_of_work,
    )


def get_create_reply_service(
    comment_repository: CommentRepo, community_port: CommunityPort, unit_of_work: Uow
) -> CreateReplyService:
    return CreateReplyService(
        comment_repository=comment_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_update_comment_service(
    comment_repository: CommentRepo,
    comment_revision_repository: CommentRevisionRepo,
    community_port: CommunityPort,
    unit_of_work: Uow,
) -> UpdateCommentService:
    return UpdateCommentService(
        comment_repository=comment_repository,
        comment_revision_repository=comment_revision_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_delete_comment_service(
    comment_repository: CommentRepo, community_port: CommunityPort, unit_of_work: Uow
) -> DeleteCommentService:
    return DeleteCommentService(
        comment_repository=comment_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_publish_comment_service(
    comment_repository: CommentRepo, community_port: CommunityPort, unit_of_work: Uow
) -> PublishCommentService:
    return PublishCommentService(
        comment_repository=comment_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_archive_comment_service(
    comment_repository: CommentRepo, community_port: CommunityPort, unit_of_work: Uow
) -> ArchiveCommentService:
    return ArchiveCommentService(
        comment_repository=comment_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_restore_comment_service(
    comment_repository: CommentRepo, community_port: CommunityPort, unit_of_work: Uow
) -> RestoreCommentService:
    return RestoreCommentService(
        comment_repository=comment_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_list_comments_service(comment_repository: CommentRepo) -> ListCommentsService:
    return ListCommentsService(comment_repository=comment_repository)


def get_list_replies_service(comment_repository: CommentRepo) -> ListRepliesService:
    return ListRepliesService(comment_repository=comment_repository)


def get_thread_service(comment_repository: CommentRepo) -> GetThreadService:
    return GetThreadService(comment_repository=comment_repository)


def get_search_comments_service(comment_repository: CommentRepo) -> SearchCommentsService:
    return SearchCommentsService(comment_repository=comment_repository)


def get_manage_comment_attachments_service(
    comment_attachment_repository: CommentAttachmentRepo,
    comment_repository: CommentRepo,
    community_port: CommunityPort,
    document_port: DocumentPort,
    unit_of_work: Uow,
) -> ManageCommentAttachmentsService:
    return ManageCommentAttachmentsService(
        comment_attachment_repository=comment_attachment_repository,
        comment_repository=comment_repository,
        community_query_port=community_port,
        document_query_port=document_port,
        unit_of_work=unit_of_work,
    )


def get_comment_revision_query_service(
    comment_revision_repository: CommentRevisionRepo,
) -> CommentRevisionQueryService:
    return CommentRevisionQueryService(comment_revision_repository=comment_revision_repository)


GetCommentQS = Annotated[GetCommentService, Depends(get_get_comment_service)]
CreateCommentUseCase = Annotated[CreateCommentService, Depends(get_create_comment_service)]
CreateReplyUseCase = Annotated[CreateReplyService, Depends(get_create_reply_service)]
UpdateCommentUseCase = Annotated[UpdateCommentService, Depends(get_update_comment_service)]
DeleteCommentUseCase = Annotated[DeleteCommentService, Depends(get_delete_comment_service)]
PublishCommentUseCase = Annotated[PublishCommentService, Depends(get_publish_comment_service)]
ArchiveCommentUseCase = Annotated[ArchiveCommentService, Depends(get_archive_comment_service)]
RestoreCommentUseCase = Annotated[RestoreCommentService, Depends(get_restore_comment_service)]
ListCommentsUseCase = Annotated[ListCommentsService, Depends(get_list_comments_service)]
ListRepliesUseCase = Annotated[ListRepliesService, Depends(get_list_replies_service)]
GetThreadUseCase = Annotated[GetThreadService, Depends(get_thread_service)]
SearchCommentsUseCase = Annotated[SearchCommentsService, Depends(get_search_comments_service)]
ManageCommentAttachmentsUseCase = Annotated[
    ManageCommentAttachmentsService, Depends(get_manage_comment_attachments_service)
]
CommentRevisionQS = Annotated[
    CommentRevisionQueryService, Depends(get_comment_revision_query_service)
]
