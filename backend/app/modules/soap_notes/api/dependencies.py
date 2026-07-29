"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and use cases
for this module — the wiring a future `api/endpoints/*.py` route module
will `Depends()` on. Every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`CreateSOAPNote`/`UpdateSOAPNote` need the Clinical Notes module's public
facade, built via its own `build_clinical_note_facade` composition root
(bound to the same `session`) rather than duplicating facade
construction here — the same pattern `app.modules.attachments.api
.dependencies` established for its own peer-module facades.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.clinical_notes.container import build_clinical_note_facade
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.soap_notes.application.services.soap_note_query_service import (
    SOAPNoteQueryService,
)
from app.modules.soap_notes.application.use_cases.create_soap_note import CreateSOAPNote
from app.modules.soap_notes.application.use_cases.update_soap_note import UpdateSOAPNote
from app.modules.soap_notes.domain.repositories import SOAPNoteRepository
from app.modules.soap_notes.infrastructure.repositories import SqlAlchemySOAPNoteRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_soap_note_repository(session: DbSession) -> SOAPNoteRepository:
    return SqlAlchemySOAPNoteRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_clinical_note_query_port(session: DbSession) -> ClinicalNoteQueryPort:
    return build_clinical_note_facade(session)


SOAPNoteRepo = Annotated[SOAPNoteRepository, Depends(get_soap_note_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
ClinicalNotePort = Annotated[ClinicalNoteQueryPort, Depends(get_clinical_note_query_port)]


def get_soap_note_query_service(soap_note_repository: SOAPNoteRepo) -> SOAPNoteQueryService:
    return SOAPNoteQueryService(soap_note_repository=soap_note_repository)


def get_create_soap_note_use_case(
    soap_note_repository: SOAPNoteRepo,
    clinical_note_query_port: ClinicalNotePort,
    unit_of_work: Uow,
) -> CreateSOAPNote:
    return CreateSOAPNote(
        soap_note_repository=soap_note_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


def get_update_soap_note_use_case(
    soap_note_repository: SOAPNoteRepo,
    clinical_note_query_port: ClinicalNotePort,
    unit_of_work: Uow,
) -> UpdateSOAPNote:
    return UpdateSOAPNote(
        soap_note_repository=soap_note_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )
