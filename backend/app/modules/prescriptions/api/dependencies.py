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
pattern `app.modules.soap_notes.api.dependencies` established.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.clinical_notes.container import build_clinical_note_facade
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.prescriptions.application.services.prescription_query_service import (
    PrescriptionQueryService,
)
from app.modules.prescriptions.application.use_cases.add_prescription_item import (
    AddPrescriptionItem,
)
from app.modules.prescriptions.application.use_cases.create_prescription import CreatePrescription
from app.modules.prescriptions.application.use_cases.finalize_prescription import (
    FinalizePrescription,
)
from app.modules.prescriptions.application.use_cases.update_prescription import UpdatePrescription
from app.modules.prescriptions.domain.repositories import (
    PrescriptionItemRepository,
    PrescriptionRepository,
)
from app.modules.prescriptions.infrastructure.repositories import (
    SqlAlchemyPrescriptionItemRepository,
    SqlAlchemyPrescriptionRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_prescription_repository(session: DbSession) -> PrescriptionRepository:
    return SqlAlchemyPrescriptionRepository(session)


def get_prescription_item_repository(session: DbSession) -> PrescriptionItemRepository:
    return SqlAlchemyPrescriptionItemRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_clinical_note_query_port(session: DbSession) -> ClinicalNoteQueryPort:
    return build_clinical_note_facade(session)


PrescriptionRepo = Annotated[PrescriptionRepository, Depends(get_prescription_repository)]
PrescriptionItemRepo = Annotated[
    PrescriptionItemRepository, Depends(get_prescription_item_repository)
]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
ClinicalNotePort = Annotated[ClinicalNoteQueryPort, Depends(get_clinical_note_query_port)]


def get_prescription_query_service(
    prescription_repository: PrescriptionRepo,
    prescription_item_repository: PrescriptionItemRepo,
) -> PrescriptionQueryService:
    return PrescriptionQueryService(
        prescription_repository=prescription_repository,
        prescription_item_repository=prescription_item_repository,
    )


def get_create_prescription_use_case(
    prescription_repository: PrescriptionRepo,
    clinical_note_query_port: ClinicalNotePort,
    unit_of_work: Uow,
) -> CreatePrescription:
    return CreatePrescription(
        prescription_repository=prescription_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


def get_update_prescription_use_case(
    prescription_repository: PrescriptionRepo,
    clinical_note_query_port: ClinicalNotePort,
    unit_of_work: Uow,
) -> UpdatePrescription:
    return UpdatePrescription(
        prescription_repository=prescription_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


def get_add_prescription_item_use_case(
    prescription_repository: PrescriptionRepo,
    prescription_item_repository: PrescriptionItemRepo,
    clinical_note_query_port: ClinicalNotePort,
    unit_of_work: Uow,
) -> AddPrescriptionItem:
    return AddPrescriptionItem(
        prescription_repository=prescription_repository,
        prescription_item_repository=prescription_item_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


def get_finalize_prescription_use_case(
    prescription_repository: PrescriptionRepo,
    prescription_item_repository: PrescriptionItemRepo,
    clinical_note_query_port: ClinicalNotePort,
    unit_of_work: Uow,
) -> FinalizePrescription:
    return FinalizePrescription(
        prescription_repository=prescription_repository,
        prescription_item_repository=prescription_item_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )
