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
(or any of their repositories) directly, the same "consume a peer module
only through its own container factory" rule
`app.modules.community.container`/`app.modules.medical_topics.container`/
`app.modules.documents.container`'s own docstrings establish for
themselves.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.community.container import build_community_facade
from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_posts.application.services.archive_post_service import (
    ArchivePostService,
)
from app.modules.community_posts.application.services.browse_author_posts_service import (
    BrowseAuthorPostsService,
)
from app.modules.community_posts.application.services.browse_community_feed_service import (
    BrowseCommunityFeedService,
)
from app.modules.community_posts.application.services.browse_topic_feed_service import (
    BrowseTopicFeedService,
)
from app.modules.community_posts.application.services.create_post_service import CreatePostService
from app.modules.community_posts.application.services.delete_post_service import DeletePostService
from app.modules.community_posts.application.services.feature_post_service import (
    FeaturePostService,
)
from app.modules.community_posts.application.services.lock_post_service import LockPostService
from app.modules.community_posts.application.services.manage_post_attachments_service import (
    ManagePostAttachmentsService,
)
from app.modules.community_posts.application.services.manage_post_tags_service import (
    ManagePostTagsService,
)
from app.modules.community_posts.application.services.manage_post_topics_service import (
    ManagePostTopicsService,
)
from app.modules.community_posts.application.services.pin_post_service import PinPostService
from app.modules.community_posts.application.services.post_query_service import (
    GetPostService,
    ListPostsService,
)
from app.modules.community_posts.application.services.publish_post_service import (
    PublishPostService,
)
from app.modules.community_posts.application.services.search_posts_service import (
    SearchPostsService,
)
from app.modules.community_posts.application.services.update_post_service import UpdatePostService
from app.modules.community_posts.domain.repositories import (
    CommunityPostAttachmentRepository,
    CommunityPostRepository,
    CommunityPostTagRepository,
    CommunityPostTopicRepository,
)
from app.modules.community_posts.infrastructure.repositories import (
    SqlAlchemyCommunityPostAttachmentRepository,
    SqlAlchemyCommunityPostRepository,
    SqlAlchemyCommunityPostTagRepository,
    SqlAlchemyCommunityPostTopicRepository,
)
from app.modules.documents.container import build_document_facade
from app.modules.documents.public.interfaces import DocumentQueryPort
from app.modules.medical_topics.container import build_topic_facade
from app.modules.medical_topics.public.interfaces import TopicQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_post_repository(session: DbSession) -> CommunityPostRepository:
    return SqlAlchemyCommunityPostRepository(session)


def get_post_topic_repository(session: DbSession) -> CommunityPostTopicRepository:
    return SqlAlchemyCommunityPostTopicRepository(session)


def get_post_tag_repository(session: DbSession) -> CommunityPostTagRepository:
    return SqlAlchemyCommunityPostTagRepository(session)


def get_post_attachment_repository(session: DbSession) -> CommunityPostAttachmentRepository:
    return SqlAlchemyCommunityPostAttachmentRepository(session)


def get_community_query_port(session: DbSession) -> CommunityQueryPort:
    return build_community_facade(session)


def get_topic_query_port(session: DbSession) -> TopicQueryPort:
    return build_topic_facade(session)


def get_document_query_port(session: DbSession) -> DocumentQueryPort:
    return build_document_facade(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


PostRepo = Annotated[CommunityPostRepository, Depends(get_post_repository)]
PostTopicRepo = Annotated[CommunityPostTopicRepository, Depends(get_post_topic_repository)]
PostTagRepo = Annotated[CommunityPostTagRepository, Depends(get_post_tag_repository)]
PostAttachmentRepo = Annotated[
    CommunityPostAttachmentRepository, Depends(get_post_attachment_repository)
]
CommunityPort = Annotated[CommunityQueryPort, Depends(get_community_query_port)]
TopicPort = Annotated[TopicQueryPort, Depends(get_topic_query_port)]
DocumentPort = Annotated[DocumentQueryPort, Depends(get_document_query_port)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]


def get_get_post_service(
    post_repository: PostRepo, community_port: CommunityPort
) -> GetPostService:
    return GetPostService(post_repository=post_repository, community_query_port=community_port)


def get_list_posts_service(post_repository: PostRepo) -> ListPostsService:
    return ListPostsService(post_repository=post_repository)


def get_search_posts_service(post_repository: PostRepo) -> SearchPostsService:
    return SearchPostsService(post_repository=post_repository)


def get_create_post_service(
    post_repository: PostRepo,
    post_topic_repository: PostTopicRepo,
    post_tag_repository: PostTagRepo,
    community_port: CommunityPort,
    topic_port: TopicPort,
    unit_of_work: Uow,
) -> CreatePostService:
    return CreatePostService(
        post_repository=post_repository,
        post_topic_repository=post_topic_repository,
        post_tag_repository=post_tag_repository,
        community_query_port=community_port,
        topic_query_port=topic_port,
        unit_of_work=unit_of_work,
    )


def get_update_post_service(
    post_repository: PostRepo, community_port: CommunityPort, unit_of_work: Uow
) -> UpdatePostService:
    return UpdatePostService(
        post_repository=post_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_delete_post_service(
    post_repository: PostRepo, community_port: CommunityPort, unit_of_work: Uow
) -> DeletePostService:
    return DeletePostService(
        post_repository=post_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_publish_post_service(
    post_repository: PostRepo, community_port: CommunityPort, unit_of_work: Uow
) -> PublishPostService:
    return PublishPostService(
        post_repository=post_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_archive_post_service(
    post_repository: PostRepo, community_port: CommunityPort, unit_of_work: Uow
) -> ArchivePostService:
    return ArchivePostService(
        post_repository=post_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_pin_post_service(
    post_repository: PostRepo, community_port: CommunityPort, unit_of_work: Uow
) -> PinPostService:
    return PinPostService(
        post_repository=post_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_lock_post_service(
    post_repository: PostRepo, community_port: CommunityPort, unit_of_work: Uow
) -> LockPostService:
    return LockPostService(
        post_repository=post_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_feature_post_service(
    post_repository: PostRepo, community_port: CommunityPort, unit_of_work: Uow
) -> FeaturePostService:
    return FeaturePostService(
        post_repository=post_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_browse_community_feed_service(
    post_repository: PostRepo, community_port: CommunityPort
) -> BrowseCommunityFeedService:
    return BrowseCommunityFeedService(
        post_repository=post_repository, community_query_port=community_port
    )


def get_browse_topic_feed_service(
    post_repository: PostRepo, topic_port: TopicPort
) -> BrowseTopicFeedService:
    return BrowseTopicFeedService(post_repository=post_repository, topic_query_port=topic_port)


def get_browse_author_posts_service(post_repository: PostRepo) -> BrowseAuthorPostsService:
    return BrowseAuthorPostsService(post_repository=post_repository)


def get_manage_post_topics_service(
    post_topic_repository: PostTopicRepo,
    post_repository: PostRepo,
    community_port: CommunityPort,
    topic_port: TopicPort,
    unit_of_work: Uow,
) -> ManagePostTopicsService:
    return ManagePostTopicsService(
        post_topic_repository=post_topic_repository,
        post_repository=post_repository,
        community_query_port=community_port,
        topic_query_port=topic_port,
        unit_of_work=unit_of_work,
    )


def get_manage_post_tags_service(
    post_tag_repository: PostTagRepo,
    post_repository: PostRepo,
    community_port: CommunityPort,
    unit_of_work: Uow,
) -> ManagePostTagsService:
    return ManagePostTagsService(
        post_tag_repository=post_tag_repository,
        post_repository=post_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_manage_post_attachments_service(
    post_attachment_repository: PostAttachmentRepo,
    post_repository: PostRepo,
    community_port: CommunityPort,
    document_port: DocumentPort,
    unit_of_work: Uow,
) -> ManagePostAttachmentsService:
    return ManagePostAttachmentsService(
        post_attachment_repository=post_attachment_repository,
        post_repository=post_repository,
        community_query_port=community_port,
        document_query_port=document_port,
        unit_of_work=unit_of_work,
    )


GetPostQS = Annotated[GetPostService, Depends(get_get_post_service)]
ListPostsQS = Annotated[ListPostsService, Depends(get_list_posts_service)]
SearchPostsUseCase = Annotated[SearchPostsService, Depends(get_search_posts_service)]
CreatePostUseCase = Annotated[CreatePostService, Depends(get_create_post_service)]
UpdatePostUseCase = Annotated[UpdatePostService, Depends(get_update_post_service)]
DeletePostUseCase = Annotated[DeletePostService, Depends(get_delete_post_service)]
PublishPostUseCase = Annotated[PublishPostService, Depends(get_publish_post_service)]
ArchivePostUseCase = Annotated[ArchivePostService, Depends(get_archive_post_service)]
PinPostUseCase = Annotated[PinPostService, Depends(get_pin_post_service)]
LockPostUseCase = Annotated[LockPostService, Depends(get_lock_post_service)]
FeaturePostUseCase = Annotated[FeaturePostService, Depends(get_feature_post_service)]
BrowseCommunityFeedUseCase = Annotated[
    BrowseCommunityFeedService, Depends(get_browse_community_feed_service)
]
BrowseTopicFeedUseCase = Annotated[BrowseTopicFeedService, Depends(get_browse_topic_feed_service)]
BrowseAuthorPostsUseCase = Annotated[
    BrowseAuthorPostsService, Depends(get_browse_author_posts_service)
]
ManagePostTopicsUseCase = Annotated[
    ManagePostTopicsService, Depends(get_manage_post_topics_service)
]
ManagePostTagsUseCase = Annotated[ManagePostTagsService, Depends(get_manage_post_tags_service)]
ManagePostAttachmentsUseCase = Annotated[
    ManagePostAttachmentsService, Depends(get_manage_post_attachments_service)
]
