"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and services
for this module — every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`get_community_query_port`/`get_topic_query_port`/`get_document_query_port`
call each peer module's own `build_*_facade(session)` composition-root
factory — never construct `CommunityFacade`/`TopicFacade`/`DocumentFacade`
(or any of their repositories) directly, the same rule
`app.modules.community_posts.presentation.dependencies` already
establishes for itself.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.community.container import build_community_facade
from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_questions.application.services.archive_question_service import (
    ArchiveQuestionService,
)
from app.modules.community_questions.application.services.browse_author_questions_service import (
    BrowseAuthorQuestionsService,
)
from app.modules.community_questions.application.services.browse_community_questions_service import (  # noqa: E501
    BrowseCommunityQuestionsService,
)
from app.modules.community_questions.application.services.browse_topic_questions_service import (
    BrowseTopicQuestionsService,
)
from app.modules.community_questions.application.services.close_question_service import (
    CloseQuestionService,
)
from app.modules.community_questions.application.services.create_question_service import (
    CreateQuestionService,
)
from app.modules.community_questions.application.services.delete_question_service import (
    DeleteQuestionService,
)
from app.modules.community_questions.application.services.feature_question_service import (
    FeatureQuestionService,
)
from app.modules.community_questions.application.services.manage_question_attachments_service import (  # noqa: E501
    ManageQuestionAttachmentsService,
)
from app.modules.community_questions.application.services.manage_question_followers_service import (
    ManageQuestionFollowersService,
)
from app.modules.community_questions.application.services.manage_question_tags_service import (
    ManageQuestionTagsService,
)
from app.modules.community_questions.application.services.manage_question_topics_service import (
    ManageQuestionTopicsService,
)
from app.modules.community_questions.application.services.pin_question_service import (
    PinQuestionService,
)
from app.modules.community_questions.application.services.publish_question_service import (
    PublishQuestionService,
)
from app.modules.community_questions.application.services.question_query_service import (
    GetQuestionService,
    ListQuestionsService,
)
from app.modules.community_questions.application.services.reopen_question_service import (
    ReopenQuestionService,
)
from app.modules.community_questions.application.services.search_questions_service import (
    SearchQuestionsService,
)
from app.modules.community_questions.application.services.update_question_service import (
    UpdateQuestionService,
)
from app.modules.community_questions.domain.repositories import (
    CommunityQuestionAttachmentRepository,
    CommunityQuestionFollowerRepository,
    CommunityQuestionRepository,
    CommunityQuestionTagRepository,
    CommunityQuestionTopicRepository,
)
from app.modules.community_questions.infrastructure.repositories import (
    SqlAlchemyCommunityQuestionAttachmentRepository,
    SqlAlchemyCommunityQuestionFollowerRepository,
    SqlAlchemyCommunityQuestionRepository,
    SqlAlchemyCommunityQuestionTagRepository,
    SqlAlchemyCommunityQuestionTopicRepository,
)
from app.modules.documents.container import build_document_facade
from app.modules.documents.public.interfaces import DocumentQueryPort
from app.modules.medical_topics.container import build_topic_facade
from app.modules.medical_topics.public.interfaces import TopicQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_question_repository(session: DbSession) -> CommunityQuestionRepository:
    return SqlAlchemyCommunityQuestionRepository(session)


def get_question_topic_repository(session: DbSession) -> CommunityQuestionTopicRepository:
    return SqlAlchemyCommunityQuestionTopicRepository(session)


def get_question_tag_repository(session: DbSession) -> CommunityQuestionTagRepository:
    return SqlAlchemyCommunityQuestionTagRepository(session)


def get_question_attachment_repository(
    session: DbSession,
) -> CommunityQuestionAttachmentRepository:
    return SqlAlchemyCommunityQuestionAttachmentRepository(session)


def get_question_follower_repository(session: DbSession) -> CommunityQuestionFollowerRepository:
    return SqlAlchemyCommunityQuestionFollowerRepository(session)


def get_community_query_port(session: DbSession) -> CommunityQueryPort:
    return build_community_facade(session)


def get_topic_query_port(session: DbSession) -> TopicQueryPort:
    return build_topic_facade(session)


def get_document_query_port(session: DbSession) -> DocumentQueryPort:
    return build_document_facade(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


QuestionRepo = Annotated[CommunityQuestionRepository, Depends(get_question_repository)]
QuestionTopicRepo = Annotated[
    CommunityQuestionTopicRepository, Depends(get_question_topic_repository)
]
QuestionTagRepo = Annotated[CommunityQuestionTagRepository, Depends(get_question_tag_repository)]
QuestionAttachmentRepo = Annotated[
    CommunityQuestionAttachmentRepository, Depends(get_question_attachment_repository)
]
QuestionFollowerRepo = Annotated[
    CommunityQuestionFollowerRepository, Depends(get_question_follower_repository)
]
CommunityPort = Annotated[CommunityQueryPort, Depends(get_community_query_port)]
TopicPort = Annotated[TopicQueryPort, Depends(get_topic_query_port)]
DocumentPort = Annotated[DocumentQueryPort, Depends(get_document_query_port)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]


def get_get_question_service(
    question_repository: QuestionRepo, community_port: CommunityPort
) -> GetQuestionService:
    return GetQuestionService(
        question_repository=question_repository, community_query_port=community_port
    )


def get_list_questions_service(question_repository: QuestionRepo) -> ListQuestionsService:
    return ListQuestionsService(question_repository=question_repository)


def get_search_questions_service(question_repository: QuestionRepo) -> SearchQuestionsService:
    return SearchQuestionsService(question_repository=question_repository)


def get_create_question_service(
    question_repository: QuestionRepo,
    question_topic_repository: QuestionTopicRepo,
    question_tag_repository: QuestionTagRepo,
    community_port: CommunityPort,
    topic_port: TopicPort,
    unit_of_work: Uow,
) -> CreateQuestionService:
    return CreateQuestionService(
        question_repository=question_repository,
        question_topic_repository=question_topic_repository,
        question_tag_repository=question_tag_repository,
        community_query_port=community_port,
        topic_query_port=topic_port,
        unit_of_work=unit_of_work,
    )


def get_update_question_service(
    question_repository: QuestionRepo, community_port: CommunityPort, unit_of_work: Uow
) -> UpdateQuestionService:
    return UpdateQuestionService(
        question_repository=question_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_delete_question_service(
    question_repository: QuestionRepo, community_port: CommunityPort, unit_of_work: Uow
) -> DeleteQuestionService:
    return DeleteQuestionService(
        question_repository=question_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_publish_question_service(
    question_repository: QuestionRepo, community_port: CommunityPort, unit_of_work: Uow
) -> PublishQuestionService:
    return PublishQuestionService(
        question_repository=question_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_archive_question_service(
    question_repository: QuestionRepo, community_port: CommunityPort, unit_of_work: Uow
) -> ArchiveQuestionService:
    return ArchiveQuestionService(
        question_repository=question_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_close_question_service(
    question_repository: QuestionRepo, community_port: CommunityPort, unit_of_work: Uow
) -> CloseQuestionService:
    return CloseQuestionService(
        question_repository=question_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_reopen_question_service(
    question_repository: QuestionRepo, community_port: CommunityPort, unit_of_work: Uow
) -> ReopenQuestionService:
    return ReopenQuestionService(
        question_repository=question_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_pin_question_service(
    question_repository: QuestionRepo, community_port: CommunityPort, unit_of_work: Uow
) -> PinQuestionService:
    return PinQuestionService(
        question_repository=question_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_feature_question_service(
    question_repository: QuestionRepo, community_port: CommunityPort, unit_of_work: Uow
) -> FeatureQuestionService:
    return FeatureQuestionService(
        question_repository=question_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_browse_community_questions_service(
    question_repository: QuestionRepo, community_port: CommunityPort
) -> BrowseCommunityQuestionsService:
    return BrowseCommunityQuestionsService(
        question_repository=question_repository, community_query_port=community_port
    )


def get_browse_topic_questions_service(
    question_repository: QuestionRepo, topic_port: TopicPort
) -> BrowseTopicQuestionsService:
    return BrowseTopicQuestionsService(
        question_repository=question_repository, topic_query_port=topic_port
    )


def get_browse_author_questions_service(
    question_repository: QuestionRepo,
) -> BrowseAuthorQuestionsService:
    return BrowseAuthorQuestionsService(question_repository=question_repository)


def get_manage_question_topics_service(
    question_topic_repository: QuestionTopicRepo,
    question_repository: QuestionRepo,
    community_port: CommunityPort,
    topic_port: TopicPort,
    unit_of_work: Uow,
) -> ManageQuestionTopicsService:
    return ManageQuestionTopicsService(
        question_topic_repository=question_topic_repository,
        question_repository=question_repository,
        community_query_port=community_port,
        topic_query_port=topic_port,
        unit_of_work=unit_of_work,
    )


def get_manage_question_tags_service(
    question_tag_repository: QuestionTagRepo,
    question_repository: QuestionRepo,
    community_port: CommunityPort,
    unit_of_work: Uow,
) -> ManageQuestionTagsService:
    return ManageQuestionTagsService(
        question_tag_repository=question_tag_repository,
        question_repository=question_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_manage_question_attachments_service(
    question_attachment_repository: QuestionAttachmentRepo,
    question_repository: QuestionRepo,
    community_port: CommunityPort,
    document_port: DocumentPort,
    unit_of_work: Uow,
) -> ManageQuestionAttachmentsService:
    return ManageQuestionAttachmentsService(
        question_attachment_repository=question_attachment_repository,
        question_repository=question_repository,
        community_query_port=community_port,
        document_query_port=document_port,
        unit_of_work=unit_of_work,
    )


def get_manage_question_followers_service(
    question_follower_repository: QuestionFollowerRepo,
    question_repository: QuestionRepo,
    community_port: CommunityPort,
    unit_of_work: Uow,
) -> ManageQuestionFollowersService:
    return ManageQuestionFollowersService(
        question_follower_repository=question_follower_repository,
        question_repository=question_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


GetQuestionQS = Annotated[GetQuestionService, Depends(get_get_question_service)]
ListQuestionsQS = Annotated[ListQuestionsService, Depends(get_list_questions_service)]
SearchQuestionsUseCase = Annotated[SearchQuestionsService, Depends(get_search_questions_service)]
CreateQuestionUseCase = Annotated[CreateQuestionService, Depends(get_create_question_service)]
UpdateQuestionUseCase = Annotated[UpdateQuestionService, Depends(get_update_question_service)]
DeleteQuestionUseCase = Annotated[DeleteQuestionService, Depends(get_delete_question_service)]
PublishQuestionUseCase = Annotated[PublishQuestionService, Depends(get_publish_question_service)]
ArchiveQuestionUseCase = Annotated[ArchiveQuestionService, Depends(get_archive_question_service)]
CloseQuestionUseCase = Annotated[CloseQuestionService, Depends(get_close_question_service)]
ReopenQuestionUseCase = Annotated[ReopenQuestionService, Depends(get_reopen_question_service)]
PinQuestionUseCase = Annotated[PinQuestionService, Depends(get_pin_question_service)]
FeatureQuestionUseCase = Annotated[FeatureQuestionService, Depends(get_feature_question_service)]
BrowseCommunityQuestionsUseCase = Annotated[
    BrowseCommunityQuestionsService, Depends(get_browse_community_questions_service)
]
BrowseTopicQuestionsUseCase = Annotated[
    BrowseTopicQuestionsService, Depends(get_browse_topic_questions_service)
]
BrowseAuthorQuestionsUseCase = Annotated[
    BrowseAuthorQuestionsService, Depends(get_browse_author_questions_service)
]
ManageQuestionTopicsUseCase = Annotated[
    ManageQuestionTopicsService, Depends(get_manage_question_topics_service)
]
ManageQuestionTagsUseCase = Annotated[
    ManageQuestionTagsService, Depends(get_manage_question_tags_service)
]
ManageQuestionAttachmentsUseCase = Annotated[
    ManageQuestionAttachmentsService, Depends(get_manage_question_attachments_service)
]
ManageQuestionFollowersUseCase = Annotated[
    ManageQuestionFollowersService, Depends(get_manage_question_followers_service)
]
