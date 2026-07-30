"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and use cases
for this module — the wiring a future `api/endpoints/*.py` route module
will `Depends()` on. Every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`CreatePatientHistory` needs the Doctor Review module's public facade
(the approval gate) plus seven peer modules' public facades (via
`PatientHistoryReferenceValidator`), each built via its own composition
root (`build_..._facade`, bound to the same `session`) rather than
duplicating facade construction here — the same pattern
`app.modules.doctor_review.api.dependencies` established for its own
eight peer-module facades.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.clinical_notes.container import build_clinical_note_facade
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.differential_diagnosis.container import build_differential_diagnosis_facade
from app.modules.differential_diagnosis.public.interfaces import DifferentialDiagnosisQueryPort
from app.modules.doctor_review.container import build_doctor_review_facade
from app.modules.doctor_review.public.interfaces import DoctorReviewQueryPort
from app.modules.icd10_coding.container import build_icd10_coding_facade
from app.modules.icd10_coding.public.interfaces import ICD10CodingQueryPort
from app.modules.lab_orders.container import build_lab_order_facade
from app.modules.lab_orders.public.interfaces import LabOrderQueryPort
from app.modules.lab_results.container import build_lab_result_facade
from app.modules.lab_results.public.interfaces import LabResultQueryPort
from app.modules.patient_history.application.services.patient_history_query_service import (
    PatientHistoryQueryService,
)
from app.modules.patient_history.application.services.patient_history_reference_validator import (
    PatientHistoryReferenceValidator,
)
from app.modules.patient_history.application.use_cases.create_patient_history import (
    CreatePatientHistory,
)
from app.modules.patient_history.domain.repositories import PatientHistoryRepository
from app.modules.patient_history.infrastructure.repositories import (
    SqlAlchemyPatientHistoryRepository,
)
from app.modules.prescriptions.container import build_prescription_facade
from app.modules.prescriptions.public.interfaces import PrescriptionQueryPort
from app.modules.soap_notes.container import build_soap_note_facade
from app.modules.soap_notes.public.interfaces import SOAPNoteQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_patient_history_repository(session: DbSession) -> PatientHistoryRepository:
    return SqlAlchemyPatientHistoryRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_doctor_review_query_port(session: DbSession) -> DoctorReviewQueryPort:
    return build_doctor_review_facade(session)


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


def get_differential_diagnosis_query_port(session: DbSession) -> DifferentialDiagnosisQueryPort:
    return build_differential_diagnosis_facade(session)


def get_icd10_coding_query_port(session: DbSession) -> ICD10CodingQueryPort:
    return build_icd10_coding_facade(session)


PatientHistoryRepo = Annotated[PatientHistoryRepository, Depends(get_patient_history_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
DoctorReviewPort = Annotated[DoctorReviewQueryPort, Depends(get_doctor_review_query_port)]
ClinicalNotePort = Annotated[ClinicalNoteQueryPort, Depends(get_clinical_note_query_port)]
SOAPNotePort = Annotated[SOAPNoteQueryPort, Depends(get_soap_note_query_port)]
PrescriptionPort = Annotated[PrescriptionQueryPort, Depends(get_prescription_query_port)]
LabOrderPort = Annotated[LabOrderQueryPort, Depends(get_lab_order_query_port)]
LabResultPort = Annotated[LabResultQueryPort, Depends(get_lab_result_query_port)]
DifferentialDiagnosisPort = Annotated[
    DifferentialDiagnosisQueryPort, Depends(get_differential_diagnosis_query_port)
]
ICD10CodingPort = Annotated[ICD10CodingQueryPort, Depends(get_icd10_coding_query_port)]


def get_patient_history_query_service(
    patient_history_repository: PatientHistoryRepo,
) -> PatientHistoryQueryService:
    return PatientHistoryQueryService(patient_history_repository=patient_history_repository)


def get_patient_history_reference_validator(
    clinical_note_query_port: ClinicalNotePort,
    soap_note_query_port: SOAPNotePort,
    prescription_query_port: PrescriptionPort,
    lab_order_query_port: LabOrderPort,
    lab_result_query_port: LabResultPort,
    differential_diagnosis_query_port: DifferentialDiagnosisPort,
    icd10_coding_query_port: ICD10CodingPort,
) -> PatientHistoryReferenceValidator:
    return PatientHistoryReferenceValidator(
        clinical_note_query_port=clinical_note_query_port,
        soap_note_query_port=soap_note_query_port,
        prescription_query_port=prescription_query_port,
        lab_order_query_port=lab_order_query_port,
        lab_result_query_port=lab_result_query_port,
        differential_diagnosis_query_port=differential_diagnosis_query_port,
        icd10_coding_query_port=icd10_coding_query_port,
    )


ReferenceValidator = Annotated[
    PatientHistoryReferenceValidator, Depends(get_patient_history_reference_validator)
]


def get_create_patient_history_use_case(
    patient_history_repository: PatientHistoryRepo,
    doctor_review_query_port: DoctorReviewPort,
    reference_validator: ReferenceValidator,
    unit_of_work: Uow,
) -> CreatePatientHistory:
    return CreatePatientHistory(
        patient_history_repository=patient_history_repository,
        doctor_review_query_port=doctor_review_query_port,
        reference_validator=reference_validator,
        unit_of_work=unit_of_work,
    )
