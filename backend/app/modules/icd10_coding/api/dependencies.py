"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and use cases
for this module — the wiring a future `api/endpoints/*.py` route module
will `Depends()` on. Every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`CreateICD10Coding` needs both the Clinical Notes and Differential
Diagnosis modules' public facades, each built via its own composition
root (`build_clinical_note_facade`/`build_differential_diagnosis_facade`,
bound to the same `session`) rather than duplicating facade construction
here — the same pattern `app.modules.differential_diagnosis.api
.dependencies` established for its own peer-module facade.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.clinical_notes.container import build_clinical_note_facade
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.differential_diagnosis.container import build_differential_diagnosis_facade
from app.modules.differential_diagnosis.public.interfaces import DifferentialDiagnosisQueryPort
from app.modules.icd10_coding.application.services.icd10_coding_query_service import (
    ICD10CodingQueryService,
)
from app.modules.icd10_coding.application.use_cases.approve_icd10_coding import (
    ApproveICD10Coding,
)
from app.modules.icd10_coding.application.use_cases.create_icd10_coding import (
    CreateICD10Coding,
)
from app.modules.icd10_coding.application.use_cases.mark_icd10_coding_as_primary import (
    MarkICD10CodingAsPrimary,
)
from app.modules.icd10_coding.application.use_cases.mark_icd10_coding_reviewed import (
    MarkICD10CodingReviewed,
)
from app.modules.icd10_coding.application.use_cases.reject_icd10_coding import (
    RejectICD10Coding,
)
from app.modules.icd10_coding.application.use_cases.unmark_icd10_coding_as_primary import (
    UnmarkICD10CodingAsPrimary,
)
from app.modules.icd10_coding.application.use_cases.update_icd10_coding import (
    UpdateICD10Coding,
)
from app.modules.icd10_coding.domain.repositories import ICD10CodingRepository
from app.modules.icd10_coding.infrastructure.repositories import (
    SqlAlchemyICD10CodingRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_icd10_coding_repository(session: DbSession) -> ICD10CodingRepository:
    return SqlAlchemyICD10CodingRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_clinical_note_query_port(session: DbSession) -> ClinicalNoteQueryPort:
    return build_clinical_note_facade(session)


def get_differential_diagnosis_query_port(session: DbSession) -> DifferentialDiagnosisQueryPort:
    return build_differential_diagnosis_facade(session)


ICD10CodingRepo = Annotated[ICD10CodingRepository, Depends(get_icd10_coding_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
ClinicalNotePort = Annotated[ClinicalNoteQueryPort, Depends(get_clinical_note_query_port)]
DifferentialDiagnosisPort = Annotated[
    DifferentialDiagnosisQueryPort, Depends(get_differential_diagnosis_query_port)
]


def get_icd10_coding_query_service(
    icd10_coding_repository: ICD10CodingRepo,
) -> ICD10CodingQueryService:
    return ICD10CodingQueryService(icd10_coding_repository=icd10_coding_repository)


def get_create_icd10_coding_use_case(
    icd10_coding_repository: ICD10CodingRepo,
    clinical_note_query_port: ClinicalNotePort,
    differential_diagnosis_query_port: DifferentialDiagnosisPort,
    unit_of_work: Uow,
) -> CreateICD10Coding:
    return CreateICD10Coding(
        icd10_coding_repository=icd10_coding_repository,
        clinical_note_query_port=clinical_note_query_port,
        differential_diagnosis_query_port=differential_diagnosis_query_port,
        unit_of_work=unit_of_work,
    )


def get_update_icd10_coding_use_case(
    icd10_coding_repository: ICD10CodingRepo, unit_of_work: Uow
) -> UpdateICD10Coding:
    return UpdateICD10Coding(
        icd10_coding_repository=icd10_coding_repository, unit_of_work=unit_of_work
    )


def get_mark_icd10_coding_as_primary_use_case(
    icd10_coding_repository: ICD10CodingRepo, unit_of_work: Uow
) -> MarkICD10CodingAsPrimary:
    return MarkICD10CodingAsPrimary(
        icd10_coding_repository=icd10_coding_repository, unit_of_work=unit_of_work
    )


def get_unmark_icd10_coding_as_primary_use_case(
    icd10_coding_repository: ICD10CodingRepo, unit_of_work: Uow
) -> UnmarkICD10CodingAsPrimary:
    return UnmarkICD10CodingAsPrimary(
        icd10_coding_repository=icd10_coding_repository, unit_of_work=unit_of_work
    )


def get_mark_icd10_coding_reviewed_use_case(
    icd10_coding_repository: ICD10CodingRepo, unit_of_work: Uow
) -> MarkICD10CodingReviewed:
    return MarkICD10CodingReviewed(
        icd10_coding_repository=icd10_coding_repository, unit_of_work=unit_of_work
    )


def get_approve_icd10_coding_use_case(
    icd10_coding_repository: ICD10CodingRepo, unit_of_work: Uow
) -> ApproveICD10Coding:
    return ApproveICD10Coding(
        icd10_coding_repository=icd10_coding_repository, unit_of_work=unit_of_work
    )


def get_reject_icd10_coding_use_case(
    icd10_coding_repository: ICD10CodingRepo, unit_of_work: Uow
) -> RejectICD10Coding:
    return RejectICD10Coding(
        icd10_coding_repository=icd10_coding_repository, unit_of_work=unit_of_work
    )
