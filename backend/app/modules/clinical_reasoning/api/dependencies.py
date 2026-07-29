"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and use cases
for this module — the wiring a future `api/endpoints/*.py` route module
will `Depends()` on. Every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`CreateClinicalReasoning` needs the Clinical Notes module's public
facade, built via its own `build_clinical_note_facade` composition root
(bound to the same `session`) rather than duplicating facade
construction here — the same pattern
`app.modules.lab_orders.api.dependencies` established.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.clinical_notes.container import build_clinical_note_facade
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.clinical_reasoning.application.services.clinical_reasoning_query_service import (
    ClinicalReasoningQueryService,
)
from app.modules.clinical_reasoning.application.use_cases.approve_clinical_reasoning import (
    ApproveClinicalReasoning,
)
from app.modules.clinical_reasoning.application.use_cases.create_clinical_reasoning import (
    CreateClinicalReasoning,
)
from app.modules.clinical_reasoning.application.use_cases.mark_clinical_reasoning_reviewed import (
    MarkClinicalReasoningReviewed,
)
from app.modules.clinical_reasoning.application.use_cases.reject_clinical_reasoning import (
    RejectClinicalReasoning,
)
from app.modules.clinical_reasoning.application.use_cases.update_clinical_reasoning import (
    UpdateClinicalReasoning,
)
from app.modules.clinical_reasoning.domain.repositories import ClinicalReasoningRepository
from app.modules.clinical_reasoning.infrastructure.repositories import (
    SqlAlchemyClinicalReasoningRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_clinical_reasoning_repository(session: DbSession) -> ClinicalReasoningRepository:
    return SqlAlchemyClinicalReasoningRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_clinical_note_query_port(session: DbSession) -> ClinicalNoteQueryPort:
    return build_clinical_note_facade(session)


ClinicalReasoningRepo = Annotated[
    ClinicalReasoningRepository, Depends(get_clinical_reasoning_repository)
]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
ClinicalNotePort = Annotated[ClinicalNoteQueryPort, Depends(get_clinical_note_query_port)]


def get_clinical_reasoning_query_service(
    clinical_reasoning_repository: ClinicalReasoningRepo,
) -> ClinicalReasoningQueryService:
    return ClinicalReasoningQueryService(
        clinical_reasoning_repository=clinical_reasoning_repository
    )


def get_create_clinical_reasoning_use_case(
    clinical_reasoning_repository: ClinicalReasoningRepo,
    clinical_note_query_port: ClinicalNotePort,
    unit_of_work: Uow,
) -> CreateClinicalReasoning:
    return CreateClinicalReasoning(
        clinical_reasoning_repository=clinical_reasoning_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


def get_update_clinical_reasoning_use_case(
    clinical_reasoning_repository: ClinicalReasoningRepo, unit_of_work: Uow
) -> UpdateClinicalReasoning:
    return UpdateClinicalReasoning(
        clinical_reasoning_repository=clinical_reasoning_repository, unit_of_work=unit_of_work
    )


def get_mark_clinical_reasoning_reviewed_use_case(
    clinical_reasoning_repository: ClinicalReasoningRepo, unit_of_work: Uow
) -> MarkClinicalReasoningReviewed:
    return MarkClinicalReasoningReviewed(
        clinical_reasoning_repository=clinical_reasoning_repository, unit_of_work=unit_of_work
    )


def get_approve_clinical_reasoning_use_case(
    clinical_reasoning_repository: ClinicalReasoningRepo, unit_of_work: Uow
) -> ApproveClinicalReasoning:
    return ApproveClinicalReasoning(
        clinical_reasoning_repository=clinical_reasoning_repository, unit_of_work=unit_of_work
    )


def get_reject_clinical_reasoning_use_case(
    clinical_reasoning_repository: ClinicalReasoningRepo, unit_of_work: Uow
) -> RejectClinicalReasoning:
    return RejectClinicalReasoning(
        clinical_reasoning_repository=clinical_reasoning_repository, unit_of_work=unit_of_work
    )
