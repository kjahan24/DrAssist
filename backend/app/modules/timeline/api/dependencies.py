"""Module-specific FastAPI dependency providers.

`TimelineQueryService` needs ten peer modules' public facades, each
built via its own composition root (`build_..._facade`, bound to the
same `session`) rather than duplicating facade construction here — the
same pattern `app.modules.doctor_review.api.dependencies` established
for its own eight peer-module facades. There is no repository, Unit of
Work, or use case here — this module is entirely read-only (see
`container.py`'s own scope note).
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.modules.appointment.container import build_appointment_facade
from app.modules.appointment.public.interfaces import AppointmentQueryPort
from app.modules.clinical_notes.container import build_clinical_note_facade
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.doctor_review.container import build_doctor_review_facade
from app.modules.doctor_review.public.interfaces import DoctorReviewQueryPort
from app.modules.documents.container import build_document_facade
from app.modules.documents.public.interfaces import DocumentQueryPort
from app.modules.lab_orders.container import build_lab_order_facade
from app.modules.lab_orders.public.interfaces import LabOrderQueryPort
from app.modules.lab_results.container import build_lab_result_facade
from app.modules.lab_results.public.interfaces import LabResultQueryPort
from app.modules.patient.container import build_patient_facade
from app.modules.patient.public.interfaces import PatientQueryPort
from app.modules.prescriptions.container import build_prescription_facade
from app.modules.prescriptions.public.interfaces import PrescriptionQueryPort
from app.modules.soap_notes.container import build_soap_note_facade
from app.modules.soap_notes.public.interfaces import SOAPNoteQueryPort
from app.modules.timeline.application.services.timeline_aggregation_service import (
    TimelineAggregationService,
)
from app.modules.timeline.application.services.timeline_query_service import (
    TimelineQueryService,
)
from app.modules.visit.container import build_visit_facade
from app.modules.visit.public.interfaces import VisitQueryPort


def get_appointment_query_port(session: DbSession) -> AppointmentQueryPort:
    return build_appointment_facade(session)


def get_visit_query_port(session: DbSession) -> VisitQueryPort:
    return build_visit_facade(session)


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


def get_document_query_port(session: DbSession) -> DocumentQueryPort:
    return build_document_facade(session)


def get_patient_query_port(session: DbSession) -> PatientQueryPort:
    return build_patient_facade(session)


def get_doctor_review_query_port(session: DbSession) -> DoctorReviewQueryPort:
    return build_doctor_review_facade(session)


AppointmentPort = Annotated[AppointmentQueryPort, Depends(get_appointment_query_port)]
VisitPort = Annotated[VisitQueryPort, Depends(get_visit_query_port)]
ClinicalNotePort = Annotated[ClinicalNoteQueryPort, Depends(get_clinical_note_query_port)]
SOAPNotePort = Annotated[SOAPNoteQueryPort, Depends(get_soap_note_query_port)]
PrescriptionPort = Annotated[PrescriptionQueryPort, Depends(get_prescription_query_port)]
LabOrderPort = Annotated[LabOrderQueryPort, Depends(get_lab_order_query_port)]
LabResultPort = Annotated[LabResultQueryPort, Depends(get_lab_result_query_port)]
DocumentPort = Annotated[DocumentQueryPort, Depends(get_document_query_port)]
PatientPort = Annotated[PatientQueryPort, Depends(get_patient_query_port)]
DoctorReviewPort = Annotated[DoctorReviewQueryPort, Depends(get_doctor_review_query_port)]


def get_timeline_aggregation_service(
    appointment_query_port: AppointmentPort,
    visit_query_port: VisitPort,
    clinical_note_query_port: ClinicalNotePort,
    soap_note_query_port: SOAPNotePort,
    prescription_query_port: PrescriptionPort,
    lab_order_query_port: LabOrderPort,
    lab_result_query_port: LabResultPort,
    document_query_port: DocumentPort,
    patient_query_port: PatientPort,
    doctor_review_query_port: DoctorReviewPort,
) -> TimelineAggregationService:
    return TimelineAggregationService(
        appointment_query_port=appointment_query_port,
        visit_query_port=visit_query_port,
        clinical_note_query_port=clinical_note_query_port,
        soap_note_query_port=soap_note_query_port,
        prescription_query_port=prescription_query_port,
        lab_order_query_port=lab_order_query_port,
        lab_result_query_port=lab_result_query_port,
        document_query_port=document_query_port,
        patient_query_port=patient_query_port,
        doctor_review_query_port=doctor_review_query_port,
    )


AggregationService = Annotated[
    TimelineAggregationService, Depends(get_timeline_aggregation_service)
]


def get_timeline_query_service(
    aggregation_service: AggregationService,
    patient_query_port: PatientPort,
    visit_query_port: VisitPort,
    appointment_query_port: AppointmentPort,
) -> TimelineQueryService:
    return TimelineQueryService(
        aggregation_service=aggregation_service,
        patient_query_port=patient_query_port,
        visit_query_port=visit_query_port,
        appointment_query_port=appointment_query_port,
    )


QueryService = Annotated[TimelineQueryService, Depends(get_timeline_query_service)]
