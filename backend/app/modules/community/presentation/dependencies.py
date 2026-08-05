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
from app.modules.community.application.services.community_query_service import (
    GetCommunityService,
    ListCommunitiesService,
)
from app.modules.community.application.services.create_community_service import (
    CreateCommunityService,
)
from app.modules.community.application.services.delete_community_service import (
    DeleteCommunityService,
)
from app.modules.community.application.services.join_community_service import JoinCommunityService
from app.modules.community.application.services.leave_community_service import (
    LeaveCommunityService,
)
from app.modules.community.application.services.update_community_service import (
    UpdateCommunityService,
)
from app.modules.community.domain.repositories import CommunityMemberRepository, CommunityRepository
from app.modules.community.infrastructure.repositories import (
    SqlAlchemyCommunityMemberRepository,
    SqlAlchemyCommunityRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_community_repository(session: DbSession) -> CommunityRepository:
    return SqlAlchemyCommunityRepository(session)


def get_community_member_repository(session: DbSession) -> CommunityMemberRepository:
    return SqlAlchemyCommunityMemberRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


CommunityRepo = Annotated[CommunityRepository, Depends(get_community_repository)]
CommunityMemberRepo = Annotated[CommunityMemberRepository, Depends(get_community_member_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]


def get_get_community_service(community_repository: CommunityRepo) -> GetCommunityService:
    return GetCommunityService(community_repository=community_repository)


def get_list_communities_service(community_repository: CommunityRepo) -> ListCommunitiesService:
    return ListCommunitiesService(community_repository=community_repository)


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


GetCommunityQS = Annotated[GetCommunityService, Depends(get_get_community_service)]
ListCommunitiesQS = Annotated[ListCommunitiesService, Depends(get_list_communities_service)]
CreateCommunityUseCase = Annotated[CreateCommunityService, Depends(get_create_community_service)]
UpdateCommunityUseCase = Annotated[UpdateCommunityService, Depends(get_update_community_service)]
DeleteCommunityUseCase = Annotated[DeleteCommunityService, Depends(get_delete_community_service)]
JoinCommunityUseCase = Annotated[JoinCommunityService, Depends(get_join_community_service)]
LeaveCommunityUseCase = Annotated[LeaveCommunityService, Depends(get_leave_community_service)]
