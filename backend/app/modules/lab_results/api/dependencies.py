"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and use cases
for this module — the wiring a future `api/endpoints/*.py` route module
will `Depends()` on. Every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`CreateLabResult`/`AddLabResultItem` need the Lab Orders module's public
facade, built via its own `build_lab_order_facade` composition root
(bound to the same `session`) rather than duplicating facade
construction here — the same pattern
`app.modules.prescriptions.api.dependencies` established for its own
peer-module facade.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.lab_orders.container import build_lab_order_facade
from app.modules.lab_orders.public.interfaces import LabOrderQueryPort
from app.modules.lab_results.application.services.lab_result_query_service import (
    LabResultQueryService,
)
from app.modules.lab_results.application.use_cases.add_lab_result_item import AddLabResultItem
from app.modules.lab_results.application.use_cases.create_lab_result import CreateLabResult
from app.modules.lab_results.application.use_cases.finalize_lab_result import FinalizeLabResult
from app.modules.lab_results.application.use_cases.update_lab_result import UpdateLabResult
from app.modules.lab_results.domain.repositories import (
    LabResultItemRepository,
    LabResultRepository,
)
from app.modules.lab_results.infrastructure.repositories import (
    SqlAlchemyLabResultItemRepository,
    SqlAlchemyLabResultRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_lab_result_repository(session: DbSession) -> LabResultRepository:
    return SqlAlchemyLabResultRepository(session)


def get_lab_result_item_repository(session: DbSession) -> LabResultItemRepository:
    return SqlAlchemyLabResultItemRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_lab_order_query_port(session: DbSession) -> LabOrderQueryPort:
    return build_lab_order_facade(session)


LabResultRepo = Annotated[LabResultRepository, Depends(get_lab_result_repository)]
LabResultItemRepo = Annotated[LabResultItemRepository, Depends(get_lab_result_item_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
LabOrderPort = Annotated[LabOrderQueryPort, Depends(get_lab_order_query_port)]


def get_lab_result_query_service(
    lab_result_repository: LabResultRepo, lab_result_item_repository: LabResultItemRepo
) -> LabResultQueryService:
    return LabResultQueryService(
        lab_result_repository=lab_result_repository,
        lab_result_item_repository=lab_result_item_repository,
    )


def get_create_lab_result_use_case(
    lab_result_repository: LabResultRepo,
    lab_order_query_port: LabOrderPort,
    unit_of_work: Uow,
) -> CreateLabResult:
    return CreateLabResult(
        lab_result_repository=lab_result_repository,
        lab_order_query_port=lab_order_query_port,
        unit_of_work=unit_of_work,
    )


def get_update_lab_result_use_case(
    lab_result_repository: LabResultRepo, unit_of_work: Uow
) -> UpdateLabResult:
    return UpdateLabResult(lab_result_repository=lab_result_repository, unit_of_work=unit_of_work)


def get_add_lab_result_item_use_case(
    lab_result_repository: LabResultRepo,
    lab_result_item_repository: LabResultItemRepo,
    lab_order_query_port: LabOrderPort,
    unit_of_work: Uow,
) -> AddLabResultItem:
    return AddLabResultItem(
        lab_result_repository=lab_result_repository,
        lab_result_item_repository=lab_result_item_repository,
        lab_order_query_port=lab_order_query_port,
        unit_of_work=unit_of_work,
    )


def get_finalize_lab_result_use_case(
    lab_result_repository: LabResultRepo,
    lab_result_item_repository: LabResultItemRepo,
    unit_of_work: Uow,
) -> FinalizeLabResult:
    return FinalizeLabResult(
        lab_result_repository=lab_result_repository,
        lab_result_item_repository=lab_result_item_repository,
        unit_of_work=unit_of_work,
    )
