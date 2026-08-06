"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and services
for this module — every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.medical_topics.application.services.create_topic_service import (
    CreateTopicService,
)
from app.modules.medical_topics.application.services.create_topic_specialty_service import (
    CreateTopicSpecialtyService,
)
from app.modules.medical_topics.application.services.delete_topic_service import (
    DeleteTopicService,
)
from app.modules.medical_topics.application.services.featured_topics_service import (
    FeaturedTopicsService,
)
from app.modules.medical_topics.application.services.follow_topic_service import (
    FollowTopicService,
)
from app.modules.medical_topics.application.services.manage_topic_aliases_service import (
    ManageTopicAliasesService,
)
from app.modules.medical_topics.application.services.manage_topic_relations_service import (
    ManageTopicRelationsService,
)
from app.modules.medical_topics.application.services.related_topics_service import (
    RelatedTopicsService,
)
from app.modules.medical_topics.application.services.search_topics_service import (
    SearchTopicsService,
)
from app.modules.medical_topics.application.services.topic_query_service import (
    GetTopicService,
    ListTopicsService,
    TopicFollowerQueryService,
    TopicSpecialtyQueryService,
)
from app.modules.medical_topics.application.services.trending_topics_service import (
    TrendingTopicsService,
)
from app.modules.medical_topics.application.services.unfollow_topic_service import (
    UnfollowTopicService,
)
from app.modules.medical_topics.application.services.update_topic_service import (
    UpdateTopicService,
)
from app.modules.medical_topics.domain.repositories import (
    MedicalTopicAliasRepository,
    MedicalTopicFollowerRepository,
    MedicalTopicRelationRepository,
    MedicalTopicRepository,
    TopicSpecialtyRepository,
)
from app.modules.medical_topics.infrastructure.repositories import (
    SqlAlchemyMedicalTopicAliasRepository,
    SqlAlchemyMedicalTopicFollowerRepository,
    SqlAlchemyMedicalTopicRelationRepository,
    SqlAlchemyMedicalTopicRepository,
    SqlAlchemyTopicSpecialtyRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_topic_repository(session: DbSession) -> MedicalTopicRepository:
    return SqlAlchemyMedicalTopicRepository(session)


def get_specialty_repository(session: DbSession) -> TopicSpecialtyRepository:
    return SqlAlchemyTopicSpecialtyRepository(session)


def get_follower_repository(session: DbSession) -> MedicalTopicFollowerRepository:
    return SqlAlchemyMedicalTopicFollowerRepository(session)


def get_alias_repository(session: DbSession) -> MedicalTopicAliasRepository:
    return SqlAlchemyMedicalTopicAliasRepository(session)


def get_relation_repository(session: DbSession) -> MedicalTopicRelationRepository:
    return SqlAlchemyMedicalTopicRelationRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


TopicRepo = Annotated[MedicalTopicRepository, Depends(get_topic_repository)]
SpecialtyRepo = Annotated[TopicSpecialtyRepository, Depends(get_specialty_repository)]
FollowerRepo = Annotated[MedicalTopicFollowerRepository, Depends(get_follower_repository)]
AliasRepo = Annotated[MedicalTopicAliasRepository, Depends(get_alias_repository)]
RelationRepo = Annotated[MedicalTopicRelationRepository, Depends(get_relation_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]


def get_get_topic_service(topic_repository: TopicRepo) -> GetTopicService:
    return GetTopicService(topic_repository=topic_repository)


def get_list_topics_service(topic_repository: TopicRepo) -> ListTopicsService:
    return ListTopicsService(topic_repository=topic_repository)


def get_topic_follower_query_service(
    follower_repository: FollowerRepo,
) -> TopicFollowerQueryService:
    return TopicFollowerQueryService(follower_repository=follower_repository)


def get_topic_specialty_query_service(
    specialty_repository: SpecialtyRepo,
) -> TopicSpecialtyQueryService:
    return TopicSpecialtyQueryService(specialty_repository=specialty_repository)


def get_create_topic_service(
    topic_repository: TopicRepo, specialty_repository: SpecialtyRepo, unit_of_work: Uow
) -> CreateTopicService:
    return CreateTopicService(
        topic_repository=topic_repository,
        specialty_repository=specialty_repository,
        unit_of_work=unit_of_work,
    )


def get_update_topic_service(
    topic_repository: TopicRepo, specialty_repository: SpecialtyRepo, unit_of_work: Uow
) -> UpdateTopicService:
    return UpdateTopicService(
        topic_repository=topic_repository,
        specialty_repository=specialty_repository,
        unit_of_work=unit_of_work,
    )


def get_delete_topic_service(topic_repository: TopicRepo, unit_of_work: Uow) -> DeleteTopicService:
    return DeleteTopicService(topic_repository=topic_repository, unit_of_work=unit_of_work)


def get_search_topics_service(
    topic_repository: TopicRepo, alias_repository: AliasRepo
) -> SearchTopicsService:
    return SearchTopicsService(topic_repository=topic_repository, alias_repository=alias_repository)


def get_trending_topics_service(topic_repository: TopicRepo) -> TrendingTopicsService:
    return TrendingTopicsService(topic_repository=topic_repository)


def get_featured_topics_service(
    topic_repository: TopicRepo, unit_of_work: Uow
) -> FeaturedTopicsService:
    return FeaturedTopicsService(topic_repository=topic_repository, unit_of_work=unit_of_work)


def get_related_topics_service(
    topic_repository: TopicRepo, relation_repository: RelationRepo
) -> RelatedTopicsService:
    return RelatedTopicsService(
        topic_repository=topic_repository, relation_repository=relation_repository
    )


def get_follow_topic_service(
    topic_repository: TopicRepo, follower_repository: FollowerRepo, unit_of_work: Uow
) -> FollowTopicService:
    return FollowTopicService(
        topic_repository=topic_repository,
        follower_repository=follower_repository,
        unit_of_work=unit_of_work,
    )


def get_unfollow_topic_service(
    follower_repository: FollowerRepo, unit_of_work: Uow
) -> UnfollowTopicService:
    return UnfollowTopicService(follower_repository=follower_repository, unit_of_work=unit_of_work)


def get_create_topic_specialty_service(
    specialty_repository: SpecialtyRepo, unit_of_work: Uow
) -> CreateTopicSpecialtyService:
    return CreateTopicSpecialtyService(
        specialty_repository=specialty_repository, unit_of_work=unit_of_work
    )


def get_manage_topic_aliases_service(
    alias_repository: AliasRepo, topic_repository: TopicRepo, unit_of_work: Uow
) -> ManageTopicAliasesService:
    return ManageTopicAliasesService(
        alias_repository=alias_repository,
        topic_repository=topic_repository,
        unit_of_work=unit_of_work,
    )


def get_manage_topic_relations_service(
    relation_repository: RelationRepo, topic_repository: TopicRepo, unit_of_work: Uow
) -> ManageTopicRelationsService:
    return ManageTopicRelationsService(
        relation_repository=relation_repository,
        topic_repository=topic_repository,
        unit_of_work=unit_of_work,
    )


GetTopicQS = Annotated[GetTopicService, Depends(get_get_topic_service)]
ListTopicsQS = Annotated[ListTopicsService, Depends(get_list_topics_service)]
TopicFollowerQS = Annotated[TopicFollowerQueryService, Depends(get_topic_follower_query_service)]
TopicSpecialtyQS = Annotated[TopicSpecialtyQueryService, Depends(get_topic_specialty_query_service)]
CreateTopicUseCase = Annotated[CreateTopicService, Depends(get_create_topic_service)]
UpdateTopicUseCase = Annotated[UpdateTopicService, Depends(get_update_topic_service)]
DeleteTopicUseCase = Annotated[DeleteTopicService, Depends(get_delete_topic_service)]
SearchTopicsUseCase = Annotated[SearchTopicsService, Depends(get_search_topics_service)]
TrendingTopicsUseCase = Annotated[TrendingTopicsService, Depends(get_trending_topics_service)]
FeaturedTopicsUseCase = Annotated[FeaturedTopicsService, Depends(get_featured_topics_service)]
RelatedTopicsUseCase = Annotated[RelatedTopicsService, Depends(get_related_topics_service)]
FollowTopicUseCase = Annotated[FollowTopicService, Depends(get_follow_topic_service)]
UnfollowTopicUseCase = Annotated[UnfollowTopicService, Depends(get_unfollow_topic_service)]
CreateTopicSpecialtyUseCase = Annotated[
    CreateTopicSpecialtyService, Depends(get_create_topic_specialty_service)
]
ManageTopicAliasesUseCase = Annotated[
    ManageTopicAliasesService, Depends(get_manage_topic_aliases_service)
]
ManageTopicRelationsUseCase = Annotated[
    ManageTopicRelationsService, Depends(get_manage_topic_relations_service)
]
