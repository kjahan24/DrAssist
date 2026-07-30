"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and use cases
for this module — the wiring a future `api/endpoints/*.py` route module
will `Depends()` on. Every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`CreateDoctorReview`/`UpdateDoctorReview` need eight peer modules' public
facades (Clinical Notes plus the seven consistency-checked categories),
each built via its own composition root (`build_..._facade`, bound to
the same `session`) rather than duplicating facade construction here —
the same pattern `app.modules.icd10_coding.api.dependencies` established
for its own peer-module facades.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.clinical_notes.container import build_clinical_note_facade
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.clinical_reasoning.container import build_clinical_reasoning_facade
from app.modules.clinical_reasoning.public.interfaces import ClinicalReasoningQueryPort
from app.modules.differential_diagnosis.container import build_differential_diagnosis_facade
from app.modules.differential_diagnosis.public.interfaces import DifferentialDiagnosisQueryPort
from app.modules.doctor_review.application.services.doctor_review_consistency_service import (
    DoctorReviewConsistencyService,
)
from app.modules.doctor_review.application.services.doctor_review_query_service import (
    DoctorReviewQueryService,
)
from app.modules.doctor_review.application.use_cases.approve_doctor_review import (
    ApproveDoctorReview,
)
from app.modules.doctor_review.application.use_cases.create_doctor_review import (
    CreateDoctorReview,
)
from app.modules.doctor_review.application.use_cases.reject_doctor_review import (
    RejectDoctorReview,
)
from app.modules.doctor_review.application.use_cases.return_doctor_review_for_revision import (
    ReturnDoctorReviewForRevision,
)
from app.modules.doctor_review.application.use_cases.update_doctor_review import (
    UpdateDoctorReview,
)
from app.modules.doctor_review.domain.repositories import DoctorReviewRepository
from app.modules.doctor_review.infrastructure.repositories import (
    SqlAlchemyDoctorReviewRepository,
)
from app.modules.icd10_coding.container import build_icd10_coding_facade
from app.modules.icd10_coding.public.interfaces import ICD10CodingQueryPort
from app.modules.lab_orders.container import build_lab_order_facade
from app.modules.lab_orders.public.interfaces import LabOrderQueryPort
from app.modules.lab_results.container import build_lab_result_facade
from app.modules.lab_results.public.interfaces import LabResultQueryPort
from app.modules.prescriptions.container import build_prescription_facade
from app.modules.prescriptions.public.interfaces import PrescriptionQueryPort
from app.modules.soap_notes.container import build_soap_note_facade
from app.modules.soap_notes.public.interfaces import SOAPNoteQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_doctor_review_repository(session: DbSession) -> DoctorReviewRepository:
    return SqlAlchemyDoctorReviewRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_clinical_note_query_port(session: DbSession) -> ClinicalNoteQueryPort:
    return build_clinical_note_facade(session)


def get_soap_note_query_port(session: DbSession) -> SOAPNoteQueryPort:
    return build_soap_note_facade(session)


def get_prescription_query_port(session: DbSession) -> PrescriptionQueryPort:
    return build_prescription_facade(session)


def get_lab_order_query_port(session: DbSession) -> LabOrderQueryPort:
    return build_lab_order_facade(session)


def get_lab_result_query_port(session: DbSession) -> LabResultQueryPort:
    return build_lab_result_facade(session)


def get_clinical_reasoning_query_port(session: DbSession) -> ClinicalReasoningQueryPort:
    return build_clinical_reasoning_facade(session)


def get_differential_diagnosis_query_port(session: DbSession) -> DifferentialDiagnosisQueryPort:
    return build_differential_diagnosis_facade(session)


def get_icd10_coding_query_port(session: DbSession) -> ICD10CodingQueryPort:
    return build_icd10_coding_facade(session)


DoctorReviewRepo = Annotated[DoctorReviewRepository, Depends(get_doctor_review_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
ClinicalNotePort = Annotated[ClinicalNoteQueryPort, Depends(get_clinical_note_query_port)]
SOAPNotePort = Annotated[SOAPNoteQueryPort, Depends(get_soap_note_query_port)]
PrescriptionPort = Annotated[PrescriptionQueryPort, Depends(get_prescription_query_port)]
LabOrderPort = Annotated[LabOrderQueryPort, Depends(get_lab_order_query_port)]
LabResultPort = Annotated[LabResultQueryPort, Depends(get_lab_result_query_port)]
ClinicalReasoningPort = Annotated[
    ClinicalReasoningQueryPort, Depends(get_clinical_reasoning_query_port)
]
DifferentialDiagnosisPort = Annotated[
    DifferentialDiagnosisQueryPort, Depends(get_differential_diagnosis_query_port)
]
ICD10CodingPort = Annotated[ICD10CodingQueryPort, Depends(get_icd10_coding_query_port)]


def get_doctor_review_query_service(
    doctor_review_repository: DoctorReviewRepo,
) -> DoctorReviewQueryService:
    return DoctorReviewQueryService(doctor_review_repository=doctor_review_repository)


def get_doctor_review_consistency_service(
    soap_note_query_port: SOAPNotePort,
    prescription_query_port: PrescriptionPort,
    lab_order_query_port: LabOrderPort,
    lab_result_query_port: LabResultPort,
    clinical_reasoning_query_port: ClinicalReasoningPort,
    differential_diagnosis_query_port: DifferentialDiagnosisPort,
    icd10_coding_query_port: ICD10CodingPort,
) -> DoctorReviewConsistencyService:
    return DoctorReviewConsistencyService(
        soap_note_query_port=soap_note_query_port,
        prescription_query_port=prescription_query_port,
        lab_order_query_port=lab_order_query_port,
        lab_result_query_port=lab_result_query_port,
        clinical_reasoning_query_port=clinical_reasoning_query_port,
        differential_diagnosis_query_port=differential_diagnosis_query_port,
        icd10_coding_query_port=icd10_coding_query_port,
    )


ConsistencyService = Annotated[
    DoctorReviewConsistencyService, Depends(get_doctor_review_consistency_service)
]


def get_create_doctor_review_use_case(
    doctor_review_repository: DoctorReviewRepo,
    clinical_note_query_port: ClinicalNotePort,
    consistency_service: ConsistencyService,
    unit_of_work: Uow,
) -> CreateDoctorReview:
    return CreateDoctorReview(
        doctor_review_repository=doctor_review_repository,
        clinical_note_query_port=clinical_note_query_port,
        consistency_service=consistency_service,
        unit_of_work=unit_of_work,
    )


def get_update_doctor_review_use_case(
    doctor_review_repository: DoctorReviewRepo,
    consistency_service: ConsistencyService,
    unit_of_work: Uow,
) -> UpdateDoctorReview:
    return UpdateDoctorReview(
        doctor_review_repository=doctor_review_repository,
        consistency_service=consistency_service,
        unit_of_work=unit_of_work,
    )


def get_approve_doctor_review_use_case(
    doctor_review_repository: DoctorReviewRepo, unit_of_work: Uow
) -> ApproveDoctorReview:
    return ApproveDoctorReview(
        doctor_review_repository=doctor_review_repository, unit_of_work=unit_of_work
    )


def get_reject_doctor_review_use_case(
    doctor_review_repository: DoctorReviewRepo, unit_of_work: Uow
) -> RejectDoctorReview:
    return RejectDoctorReview(
        doctor_review_repository=doctor_review_repository, unit_of_work=unit_of_work
    )


def get_return_doctor_review_for_revision_use_case(
    doctor_review_repository: DoctorReviewRepo, unit_of_work: Uow
) -> ReturnDoctorReviewForRevision:
    return ReturnDoctorReviewForRevision(
        doctor_review_repository=doctor_review_repository, unit_of_work=unit_of_work
    )
