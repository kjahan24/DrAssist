"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and use cases
for this module — the wiring a future `api/endpoints/*.py` route module
will `Depends()` on. Every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

Every use case needs the Clinical Notes module's public facade, built via
its own `build_clinical_note_facade` composition root (bound to the same
`session`) rather than duplicating facade construction here — the same
pattern `app.modules.prescriptions.api.dependencies` established.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.clinical_notes.container import build_clinical_note_facade
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.lab_orders.application.services.lab_order_query_service import (
    LabOrderQueryService,
)
from app.modules.lab_orders.application.use_cases.add_lab_order_item import AddLabOrderItem
from app.modules.lab_orders.application.use_cases.cancel_lab_order import CancelLabOrder
from app.modules.lab_orders.application.use_cases.create_lab_order import CreateLabOrder
from app.modules.lab_orders.application.use_cases.mark_lab_order_collected import (
    MarkLabOrderCollected,
)
from app.modules.lab_orders.application.use_cases.place_lab_order import PlaceLabOrder
from app.modules.lab_orders.application.use_cases.update_lab_order import UpdateLabOrder
from app.modules.lab_orders.domain.repositories import LabOrderItemRepository, LabOrderRepository
from app.modules.lab_orders.infrastructure.repositories import (
    SqlAlchemyLabOrderItemRepository,
    SqlAlchemyLabOrderRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_lab_order_repository(session: DbSession) -> LabOrderRepository:
    return SqlAlchemyLabOrderRepository(session)


def get_lab_order_item_repository(session: DbSession) -> LabOrderItemRepository:
    return SqlAlchemyLabOrderItemRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_clinical_note_query_port(session: DbSession) -> ClinicalNoteQueryPort:
    return build_clinical_note_facade(session)


LabOrderRepo = Annotated[LabOrderRepository, Depends(get_lab_order_repository)]
LabOrderItemRepo = Annotated[LabOrderItemRepository, Depends(get_lab_order_item_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
ClinicalNotePort = Annotated[ClinicalNoteQueryPort, Depends(get_clinical_note_query_port)]


def get_lab_order_query_service(
    lab_order_repository: LabOrderRepo, lab_order_item_repository: LabOrderItemRepo
) -> LabOrderQueryService:
    return LabOrderQueryService(
        lab_order_repository=lab_order_repository,
        lab_order_item_repository=lab_order_item_repository,
    )


def get_create_lab_order_use_case(
    lab_order_repository: LabOrderRepo,
    clinical_note_query_port: ClinicalNotePort,
    unit_of_work: Uow,
) -> CreateLabOrder:
    return CreateLabOrder(
        lab_order_repository=lab_order_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


def get_update_lab_order_use_case(
    lab_order_repository: LabOrderRepo,
    clinical_note_query_port: ClinicalNotePort,
    unit_of_work: Uow,
) -> UpdateLabOrder:
    return UpdateLabOrder(
        lab_order_repository=lab_order_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


def get_add_lab_order_item_use_case(
    lab_order_repository: LabOrderRepo,
    lab_order_item_repository: LabOrderItemRepo,
    clinical_note_query_port: ClinicalNotePort,
    unit_of_work: Uow,
) -> AddLabOrderItem:
    return AddLabOrderItem(
        lab_order_repository=lab_order_repository,
        lab_order_item_repository=lab_order_item_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


def get_place_lab_order_use_case(
    lab_order_repository: LabOrderRepo,
    lab_order_item_repository: LabOrderItemRepo,
    clinical_note_query_port: ClinicalNotePort,
    unit_of_work: Uow,
) -> PlaceLabOrder:
    return PlaceLabOrder(
        lab_order_repository=lab_order_repository,
        lab_order_item_repository=lab_order_item_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


def get_mark_lab_order_collected_use_case(
    lab_order_repository: LabOrderRepo,
    clinical_note_query_port: ClinicalNotePort,
    unit_of_work: Uow,
) -> MarkLabOrderCollected:
    return MarkLabOrderCollected(
        lab_order_repository=lab_order_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


def get_cancel_lab_order_use_case(
    lab_order_repository: LabOrderRepo,
    clinical_note_query_port: ClinicalNotePort,
    unit_of_work: Uow,
) -> CancelLabOrder:
    return CancelLabOrder(
        lab_order_repository=lab_order_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )
