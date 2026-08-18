"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and services
for this module — every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`get_community_query_port`/`get_question_query_port`/`get_document_query_port`
call each peer module's own `build_*_facade(session)` composition-root
factory — never construct `CommunityFacade`/`QuestionFacade`/`DocumentFacade`
(or any of their repositories) directly, the same rule
`app.modules.community_questions.presentation.dependencies` already
establishes for itself.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.community.container import build_community_facade
from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_answers.application.services.answer_query_service import (
    GetAnswerService,
    ListAnswersService,
)
from app.modules.community_answers.application.services.answer_revision_query_service import (
    AnswerRevisionQueryService,
)
from app.modules.community_answers.application.services.archive_answer_service import (
    ArchiveAnswerService,
)
from app.modules.community_answers.application.services.create_answer_service import (
    CreateAnswerService,
)
from app.modules.community_answers.application.services.delete_answer_service import (
    DeleteAnswerService,
)
from app.modules.community_answers.application.services.feature_answer_service import (
    FeatureAnswerService,
)
from app.modules.community_answers.application.services.list_author_answers_service import (
    ListAuthorAnswersService,
)
from app.modules.community_answers.application.services.list_question_answers_service import (
    ListQuestionAnswersService,
)
from app.modules.community_answers.application.services.manage_answer_attachments_service import (  # noqa: E501
    ManageAnswerAttachmentsService,
)
from app.modules.community_answers.application.services.mark_best_answer_service import (
    MarkBestAnswerService,
)
from app.modules.community_answers.application.services.pin_answer_service import PinAnswerService
from app.modules.community_answers.application.services.publish_answer_service import (
    PublishAnswerService,
)
from app.modules.community_answers.application.services.remove_best_answer_service import (
    RemoveBestAnswerService,
)
from app.modules.community_answers.application.services.restore_answer_service import (
    RestoreAnswerService,
)
from app.modules.community_answers.application.services.search_answers_service import (
    SearchAnswersService,
)
from app.modules.community_answers.application.services.update_answer_service import (
    UpdateAnswerService,
)
from app.modules.community_answers.domain.repositories import (
    CommunityAnswerAttachmentRepository,
    CommunityAnswerRepository,
    CommunityAnswerRevisionRepository,
)
from app.modules.community_answers.infrastructure.repositories import (
    SqlAlchemyCommunityAnswerAttachmentRepository,
    SqlAlchemyCommunityAnswerRepository,
    SqlAlchemyCommunityAnswerRevisionRepository,
)
from app.modules.community_questions.container import build_question_facade
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.modules.documents.container import build_document_facade
from app.modules.documents.public.interfaces import DocumentQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_answer_repository(session: DbSession) -> CommunityAnswerRepository:
    return SqlAlchemyCommunityAnswerRepository(session)


def get_answer_revision_repository(session: DbSession) -> CommunityAnswerRevisionRepository:
    return SqlAlchemyCommunityAnswerRevisionRepository(session)


def get_answer_attachment_repository(session: DbSession) -> CommunityAnswerAttachmentRepository:
    return SqlAlchemyCommunityAnswerAttachmentRepository(session)


def get_community_query_port(session: DbSession) -> CommunityQueryPort:
    return build_community_facade(session)


def get_question_query_port(session: DbSession) -> QuestionQueryPort:
    return build_question_facade(session)


def get_document_query_port(session: DbSession) -> DocumentQueryPort:
    return build_document_facade(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


AnswerRepo = Annotated[CommunityAnswerRepository, Depends(get_answer_repository)]
AnswerRevisionRepo = Annotated[
    CommunityAnswerRevisionRepository, Depends(get_answer_revision_repository)
]
AnswerAttachmentRepo = Annotated[
    CommunityAnswerAttachmentRepository, Depends(get_answer_attachment_repository)
]
CommunityPort = Annotated[CommunityQueryPort, Depends(get_community_query_port)]
QuestionPort = Annotated[QuestionQueryPort, Depends(get_question_query_port)]
DocumentPort = Annotated[DocumentQueryPort, Depends(get_document_query_port)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]


def get_get_answer_service(
    answer_repository: AnswerRepo, community_port: CommunityPort
) -> GetAnswerService:
    return GetAnswerService(
        answer_repository=answer_repository, community_query_port=community_port
    )


def get_list_answers_service(answer_repository: AnswerRepo) -> ListAnswersService:
    return ListAnswersService(answer_repository=answer_repository)


def get_search_answers_service(answer_repository: AnswerRepo) -> SearchAnswersService:
    return SearchAnswersService(answer_repository=answer_repository)


def get_create_answer_service(
    answer_repository: AnswerRepo,
    community_port: CommunityPort,
    question_port: QuestionPort,
    unit_of_work: Uow,
) -> CreateAnswerService:
    return CreateAnswerService(
        answer_repository=answer_repository,
        community_query_port=community_port,
        question_query_port=question_port,
        unit_of_work=unit_of_work,
    )


def get_update_answer_service(
    answer_repository: AnswerRepo,
    answer_revision_repository: AnswerRevisionRepo,
    community_port: CommunityPort,
    unit_of_work: Uow,
) -> UpdateAnswerService:
    return UpdateAnswerService(
        answer_repository=answer_repository,
        answer_revision_repository=answer_revision_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_delete_answer_service(
    answer_repository: AnswerRepo, community_port: CommunityPort, unit_of_work: Uow
) -> DeleteAnswerService:
    return DeleteAnswerService(
        answer_repository=answer_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_publish_answer_service(
    answer_repository: AnswerRepo, community_port: CommunityPort, unit_of_work: Uow
) -> PublishAnswerService:
    return PublishAnswerService(
        answer_repository=answer_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_archive_answer_service(
    answer_repository: AnswerRepo, community_port: CommunityPort, unit_of_work: Uow
) -> ArchiveAnswerService:
    return ArchiveAnswerService(
        answer_repository=answer_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_restore_answer_service(
    answer_repository: AnswerRepo, community_port: CommunityPort, unit_of_work: Uow
) -> RestoreAnswerService:
    return RestoreAnswerService(
        answer_repository=answer_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_mark_best_answer_service(
    answer_repository: AnswerRepo,
    community_port: CommunityPort,
    question_port: QuestionPort,
    unit_of_work: Uow,
) -> MarkBestAnswerService:
    return MarkBestAnswerService(
        answer_repository=answer_repository,
        community_query_port=community_port,
        question_query_port=question_port,
        unit_of_work=unit_of_work,
    )


def get_remove_best_answer_service(
    answer_repository: AnswerRepo,
    community_port: CommunityPort,
    question_port: QuestionPort,
    unit_of_work: Uow,
) -> RemoveBestAnswerService:
    return RemoveBestAnswerService(
        answer_repository=answer_repository,
        community_query_port=community_port,
        question_query_port=question_port,
        unit_of_work=unit_of_work,
    )


def get_feature_answer_service(
    answer_repository: AnswerRepo, community_port: CommunityPort, unit_of_work: Uow
) -> FeatureAnswerService:
    return FeatureAnswerService(
        answer_repository=answer_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_pin_answer_service(
    answer_repository: AnswerRepo, community_port: CommunityPort, unit_of_work: Uow
) -> PinAnswerService:
    return PinAnswerService(
        answer_repository=answer_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_list_question_answers_service(
    answer_repository: AnswerRepo,
) -> ListQuestionAnswersService:
    return ListQuestionAnswersService(answer_repository=answer_repository)


def get_list_author_answers_service(answer_repository: AnswerRepo) -> ListAuthorAnswersService:
    return ListAuthorAnswersService(answer_repository=answer_repository)


def get_manage_answer_attachments_service(
    answer_attachment_repository: AnswerAttachmentRepo,
    answer_repository: AnswerRepo,
    community_port: CommunityPort,
    document_port: DocumentPort,
    unit_of_work: Uow,
) -> ManageAnswerAttachmentsService:
    return ManageAnswerAttachmentsService(
        answer_attachment_repository=answer_attachment_repository,
        answer_repository=answer_repository,
        community_query_port=community_port,
        document_query_port=document_port,
        unit_of_work=unit_of_work,
    )


def get_answer_revision_query_service(
    answer_revision_repository: AnswerRevisionRepo,
) -> AnswerRevisionQueryService:
    return AnswerRevisionQueryService(answer_revision_repository=answer_revision_repository)


GetAnswerQS = Annotated[GetAnswerService, Depends(get_get_answer_service)]
ListAnswersQS = Annotated[ListAnswersService, Depends(get_list_answers_service)]
SearchAnswersUseCase = Annotated[SearchAnswersService, Depends(get_search_answers_service)]
CreateAnswerUseCase = Annotated[CreateAnswerService, Depends(get_create_answer_service)]
UpdateAnswerUseCase = Annotated[UpdateAnswerService, Depends(get_update_answer_service)]
DeleteAnswerUseCase = Annotated[DeleteAnswerService, Depends(get_delete_answer_service)]
PublishAnswerUseCase = Annotated[PublishAnswerService, Depends(get_publish_answer_service)]
ArchiveAnswerUseCase = Annotated[ArchiveAnswerService, Depends(get_archive_answer_service)]
RestoreAnswerUseCase = Annotated[RestoreAnswerService, Depends(get_restore_answer_service)]
MarkBestAnswerUseCase = Annotated[MarkBestAnswerService, Depends(get_mark_best_answer_service)]
RemoveBestAnswerUseCase = Annotated[
    RemoveBestAnswerService, Depends(get_remove_best_answer_service)
]
FeatureAnswerUseCase = Annotated[FeatureAnswerService, Depends(get_feature_answer_service)]
PinAnswerUseCase = Annotated[PinAnswerService, Depends(get_pin_answer_service)]
ListQuestionAnswersUseCase = Annotated[
    ListQuestionAnswersService, Depends(get_list_question_answers_service)
]
ListAuthorAnswersUseCase = Annotated[
    ListAuthorAnswersService, Depends(get_list_author_answers_service)
]
ManageAnswerAttachmentsUseCase = Annotated[
    ManageAnswerAttachmentsService, Depends(get_manage_answer_attachments_service)
]
AnswerRevisionQS = Annotated[AnswerRevisionQueryService, Depends(get_answer_revision_query_service)]
