"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and use cases
for this module — the wiring a future `api/endpoints/*.py` route module
will `Depends()` on. Every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`CreateDifferentialDiagnosis` needs both the Clinical Notes and Clinical
Reasoning modules' public facades, each built via its own composition
root (`build_clinical_note_facade`/`build_clinical_reasoning_facade`,
bound to the same `session`) rather than duplicating facade construction
here — the same pattern `app.modules.lab_results.api.dependencies`
established for its own peer-module facade.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.clinical_notes.container import build_clinical_note_facade
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.clinical_reasoning.container import build_clinical_reasoning_facade
from app.modules.clinical_reasoning.public.interfaces import ClinicalReasoningQueryPort
from app.modules.differential_diagnosis.application.services.differential_diagnosis_query_service import (  # noqa: E501
    DifferentialDiagnosisQueryService,
)
from app.modules.differential_diagnosis.application.use_cases.approve_differential_diagnosis import (  # noqa: E501
    ApproveDifferentialDiagnosis,
)
from app.modules.differential_diagnosis.application.use_cases.create_differential_diagnosis import (  # noqa: E501
    CreateDifferentialDiagnosis,
)
from app.modules.differential_diagnosis.application.use_cases.mark_differential_diagnosis_reviewed import (  # noqa: E501
    MarkDifferentialDiagnosisReviewed,
)
from app.modules.differential_diagnosis.application.use_cases.reject_differential_diagnosis import (  # noqa: E501
    RejectDifferentialDiagnosis,
)
from app.modules.differential_diagnosis.application.use_cases.update_differential_diagnosis import (  # noqa: E501
    UpdateDifferentialDiagnosis,
)
from app.modules.differential_diagnosis.domain.repositories import (
    DifferentialDiagnosisRepository,
)
from app.modules.differential_diagnosis.infrastructure.repositories import (
    SqlAlchemyDifferentialDiagnosisRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_differential_diagnosis_repository(
    session: DbSession,
) -> DifferentialDiagnosisRepository:
    return SqlAlchemyDifferentialDiagnosisRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_clinical_note_query_port(session: DbSession) -> ClinicalNoteQueryPort:
    return build_clinical_note_facade(session)


def get_clinical_reasoning_query_port(session: DbSession) -> ClinicalReasoningQueryPort:
    return build_clinical_reasoning_facade(session)


DifferentialDiagnosisRepo = Annotated[
    DifferentialDiagnosisRepository, Depends(get_differential_diagnosis_repository)
]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
ClinicalNotePort = Annotated[ClinicalNoteQueryPort, Depends(get_clinical_note_query_port)]
ClinicalReasoningPort = Annotated[
    ClinicalReasoningQueryPort, Depends(get_clinical_reasoning_query_port)
]


def get_differential_diagnosis_query_service(
    differential_diagnosis_repository: DifferentialDiagnosisRepo,
) -> DifferentialDiagnosisQueryService:
    return DifferentialDiagnosisQueryService(
        differential_diagnosis_repository=differential_diagnosis_repository
    )


def get_create_differential_diagnosis_use_case(
    differential_diagnosis_repository: DifferentialDiagnosisRepo,
    clinical_note_query_port: ClinicalNotePort,
    clinical_reasoning_query_port: ClinicalReasoningPort,
    unit_of_work: Uow,
) -> CreateDifferentialDiagnosis:
    return CreateDifferentialDiagnosis(
        differential_diagnosis_repository=differential_diagnosis_repository,
        clinical_note_query_port=clinical_note_query_port,
        clinical_reasoning_query_port=clinical_reasoning_query_port,
        unit_of_work=unit_of_work,
    )


def get_update_differential_diagnosis_use_case(
    differential_diagnosis_repository: DifferentialDiagnosisRepo, unit_of_work: Uow
) -> UpdateDifferentialDiagnosis:
    return UpdateDifferentialDiagnosis(
        differential_diagnosis_repository=differential_diagnosis_repository,
        unit_of_work=unit_of_work,
    )


def get_mark_differential_diagnosis_reviewed_use_case(
    differential_diagnosis_repository: DifferentialDiagnosisRepo, unit_of_work: Uow
) -> MarkDifferentialDiagnosisReviewed:
    return MarkDifferentialDiagnosisReviewed(
        differential_diagnosis_repository=differential_diagnosis_repository,
        unit_of_work=unit_of_work,
    )


def get_approve_differential_diagnosis_use_case(
    differential_diagnosis_repository: DifferentialDiagnosisRepo, unit_of_work: Uow
) -> ApproveDifferentialDiagnosis:
    return ApproveDifferentialDiagnosis(
        differential_diagnosis_repository=differential_diagnosis_repository,
        unit_of_work=unit_of_work,
    )


def get_reject_differential_diagnosis_use_case(
    differential_diagnosis_repository: DifferentialDiagnosisRepo, unit_of_work: Uow
) -> RejectDifferentialDiagnosis:
    return RejectDifferentialDiagnosis(
        differential_diagnosis_repository=differential_diagnosis_repository,
        unit_of_work=unit_of_work,
    )
