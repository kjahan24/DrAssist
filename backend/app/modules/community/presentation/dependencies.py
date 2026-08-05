"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and services
for this module — every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`get_storage_port` mirrors `app.modules.documents.api.dependencies`'s own
`get_storage_port` exactly (`@lru_cache`d, no `session` — `StoragePort`'s
one implementation, `LocalStorageProvider`, is stateless filesystem I/O
with no per-request transaction to join, the same reasoning that
module's own docstring gives for its identical wiring).
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.config import get_settings
from app.core.container import get_event_bus
from app.infrastructure.storage.local_storage_provider import LocalStorageProvider
from app.modules.community.application.services.browse_communities_service import (
    BrowseCommunitiesService,
)
from app.modules.community.application.services.community_query_service import (
    CommunityCategoryQueryService,
    CommunityMembershipQueryService,
    GetCommunityService,
    ListCommunitiesService,
)
from app.modules.community.application.services.community_statistics_service import (
    CommunityStatisticsService,
)
from app.modules.community.application.services.create_community_category_service import (
    CreateCommunityCategoryService,
)
from app.modules.community.application.services.create_community_service import (
    CreateCommunityService,
)
from app.modules.community.application.services.delete_community_service import (
    DeleteCommunityService,
)
from app.modules.community.application.services.feature_communities_service import (
    FeatureCommunitiesService,
)
from app.modules.community.application.services.join_community_service import JoinCommunityService
from app.modules.community.application.services.leave_community_service import (
    LeaveCommunityService,
)
from app.modules.community.application.services.manage_community_rules_service import (
    ManageCommunityRulesService,
)
from app.modules.community.application.services.manage_community_tags_service import (
    ManageCommunityTagsService,
)
from app.modules.community.application.services.search_communities_service import (
    SearchCommunitiesService,
)
from app.modules.community.application.services.update_community_appearance_service import (
    UpdateCommunityAppearanceService,
)
from app.modules.community.application.services.update_community_service import (
    UpdateCommunityService,
)
from app.modules.community.domain.repositories import (
    CommunityCategoryRepository,
    CommunityMemberRepository,
    CommunityRepository,
    CommunityRuleRepository,
    CommunityTagRepository,
)
from app.modules.community.infrastructure.repositories import (
    SqlAlchemyCommunityCategoryRepository,
    SqlAlchemyCommunityMemberRepository,
    SqlAlchemyCommunityRepository,
    SqlAlchemyCommunityRuleRepository,
    SqlAlchemyCommunityTagRepository,
)
from app.shared.application.storage_port import StoragePort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_community_repository(session: DbSession) -> CommunityRepository:
    return SqlAlchemyCommunityRepository(session)


def get_community_member_repository(session: DbSession) -> CommunityMemberRepository:
    return SqlAlchemyCommunityMemberRepository(session)


def get_community_category_repository(session: DbSession) -> CommunityCategoryRepository:
    return SqlAlchemyCommunityCategoryRepository(session)


def get_community_tag_repository(session: DbSession) -> CommunityTagRepository:
    return SqlAlchemyCommunityTagRepository(session)


def get_community_rule_repository(session: DbSession) -> CommunityRuleRepository:
    return SqlAlchemyCommunityRuleRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


@lru_cache
def get_storage_port() -> StoragePort:
    return LocalStorageProvider(get_settings().local_storage.base_path)


CommunityRepo = Annotated[CommunityRepository, Depends(get_community_repository)]
CommunityMemberRepo = Annotated[CommunityMemberRepository, Depends(get_community_member_repository)]
CommunityCategoryRepo = Annotated[
    CommunityCategoryRepository, Depends(get_community_category_repository)
]
CommunityTagRepo = Annotated[CommunityTagRepository, Depends(get_community_tag_repository)]
CommunityRuleRepo = Annotated[CommunityRuleRepository, Depends(get_community_rule_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
Storage = Annotated[StoragePort, Depends(get_storage_port)]


def get_get_community_service(community_repository: CommunityRepo) -> GetCommunityService:
    return GetCommunityService(community_repository=community_repository)


def get_list_communities_service(community_repository: CommunityRepo) -> ListCommunitiesService:
    return ListCommunitiesService(community_repository=community_repository)


def get_community_membership_query_service(
    community_member_repository: CommunityMemberRepo,
) -> CommunityMembershipQueryService:
    return CommunityMembershipQueryService(community_member_repository=community_member_repository)


def get_community_category_query_service(
    community_category_repository: CommunityCategoryRepo,
) -> CommunityCategoryQueryService:
    return CommunityCategoryQueryService(
        community_category_repository=community_category_repository
    )


def get_create_community_service(
    community_repository: CommunityRepo,
    community_member_repository: CommunityMemberRepo,
    unit_of_work: Uow,
) -> CreateCommunityService:
    return CreateCommunityService(
        community_repository=community_repository,
        community_member_repository=community_member_repository,
        unit_of_work=unit_of_work,
    )


def get_update_community_service(
    community_repository: CommunityRepo,
    community_member_repository: CommunityMemberRepo,
    unit_of_work: Uow,
) -> UpdateCommunityService:
    return UpdateCommunityService(
        community_repository=community_repository,
        community_member_repository=community_member_repository,
        unit_of_work=unit_of_work,
    )


def get_delete_community_service(
    community_repository: CommunityRepo,
    community_member_repository: CommunityMemberRepo,
    unit_of_work: Uow,
) -> DeleteCommunityService:
    return DeleteCommunityService(
        community_repository=community_repository,
        community_member_repository=community_member_repository,
        unit_of_work=unit_of_work,
    )


def get_join_community_service(
    community_repository: CommunityRepo,
    community_member_repository: CommunityMemberRepo,
    unit_of_work: Uow,
) -> JoinCommunityService:
    return JoinCommunityService(
        community_repository=community_repository,
        community_member_repository=community_member_repository,
        unit_of_work=unit_of_work,
    )


def get_leave_community_service(
    community_member_repository: CommunityMemberRepo, unit_of_work: Uow
) -> LeaveCommunityService:
    return LeaveCommunityService(
        community_member_repository=community_member_repository, unit_of_work=unit_of_work
    )


def get_browse_communities_service(community_repository: CommunityRepo) -> BrowseCommunitiesService:
    return BrowseCommunitiesService(community_repository=community_repository)


def get_search_communities_service(community_repository: CommunityRepo) -> SearchCommunitiesService:
    return SearchCommunitiesService(community_repository=community_repository)


def get_feature_communities_service(
    community_repository: CommunityRepo, unit_of_work: Uow
) -> FeatureCommunitiesService:
    return FeatureCommunitiesService(
        community_repository=community_repository, unit_of_work=unit_of_work
    )


def get_update_community_appearance_service(
    community_repository: CommunityRepo,
    community_member_repository: CommunityMemberRepo,
    storage_port: Storage,
    unit_of_work: Uow,
) -> UpdateCommunityAppearanceService:
    return UpdateCommunityAppearanceService(
        community_repository=community_repository,
        community_member_repository=community_member_repository,
        storage_port=storage_port,
        unit_of_work=unit_of_work,
    )


def get_manage_community_rules_service(
    community_rule_repository: CommunityRuleRepo,
    community_member_repository: CommunityMemberRepo,
    unit_of_work: Uow,
) -> ManageCommunityRulesService:
    return ManageCommunityRulesService(
        community_rule_repository=community_rule_repository,
        community_member_repository=community_member_repository,
        unit_of_work=unit_of_work,
    )


def get_manage_community_tags_service(
    community_tag_repository: CommunityTagRepo,
    community_member_repository: CommunityMemberRepo,
    unit_of_work: Uow,
) -> ManageCommunityTagsService:
    return ManageCommunityTagsService(
        community_tag_repository=community_tag_repository,
        community_member_repository=community_member_repository,
        unit_of_work=unit_of_work,
    )


def get_community_statistics_service(
    community_repository: CommunityRepo,
    community_member_repository: CommunityMemberRepo,
    community_rule_repository: CommunityRuleRepo,
    community_tag_repository: CommunityTagRepo,
) -> CommunityStatisticsService:
    return CommunityStatisticsService(
        community_repository=community_repository,
        community_member_repository=community_member_repository,
        community_rule_repository=community_rule_repository,
        community_tag_repository=community_tag_repository,
    )


def get_create_community_category_service(
    community_category_repository: CommunityCategoryRepo, unit_of_work: Uow
) -> CreateCommunityCategoryService:
    return CreateCommunityCategoryService(
        community_category_repository=community_category_repository, unit_of_work=unit_of_work
    )


GetCommunityQS = Annotated[GetCommunityService, Depends(get_get_community_service)]
ListCommunitiesQS = Annotated[ListCommunitiesService, Depends(get_list_communities_service)]
CommunityMembershipQS = Annotated[
    CommunityMembershipQueryService, Depends(get_community_membership_query_service)
]
CommunityCategoryQS = Annotated[
    CommunityCategoryQueryService, Depends(get_community_category_query_service)
]
CreateCommunityUseCase = Annotated[CreateCommunityService, Depends(get_create_community_service)]
UpdateCommunityUseCase = Annotated[UpdateCommunityService, Depends(get_update_community_service)]
DeleteCommunityUseCase = Annotated[DeleteCommunityService, Depends(get_delete_community_service)]
JoinCommunityUseCase = Annotated[JoinCommunityService, Depends(get_join_community_service)]
LeaveCommunityUseCase = Annotated[LeaveCommunityService, Depends(get_leave_community_service)]
BrowseCommunitiesUseCase = Annotated[
    BrowseCommunitiesService, Depends(get_browse_communities_service)
]
SearchCommunitiesUseCase = Annotated[
    SearchCommunitiesService, Depends(get_search_communities_service)
]
FeatureCommunitiesUseCase = Annotated[
    FeatureCommunitiesService, Depends(get_feature_communities_service)
]
UpdateCommunityAppearanceUseCase = Annotated[
    UpdateCommunityAppearanceService, Depends(get_update_community_appearance_service)
]
ManageCommunityRulesUseCase = Annotated[
    ManageCommunityRulesService, Depends(get_manage_community_rules_service)
]
ManageCommunityTagsUseCase = Annotated[
    ManageCommunityTagsService, Depends(get_manage_community_tags_service)
]
CommunityStatisticsUseCase = Annotated[
    CommunityStatisticsService, Depends(get_community_statistics_service)
]
CreateCommunityCategoryUseCase = Annotated[
    CreateCommunityCategoryService, Depends(get_create_community_category_service)
]
