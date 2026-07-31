"""Unit tests for `TimelineAggregationService`, using in-memory fakes for
all ten peer modules' public query ports."""

from datetime import datetime
from uuid import uuid4

from app.modules.appointment.public.dto import AppointmentSummaryDTO
from app.modules.clinical_notes.public.dto import ClinicalNoteSummaryDTO
from app.modules.doctor_review.public.dto import DoctorReviewSummaryDTO
from app.modules.documents.public.dto import MedicalDocumentSummaryDTO
from app.modules.lab_orders.public.dto import LabOrderSummaryDTO
from app.modules.lab_results.public.dto import LabResultSummaryDTO
from app.modules.patient.public.dto import (
    PatientAllergySummaryDTO,
    PatientMedicalConditionSummaryDTO,
    PatientSummaryDTO,
)
from app.modules.prescriptions.public.dto import PrescriptionSummaryDTO
from app.modules.soap_notes.public.dto import SOAPNoteSummaryDTO
from app.modules.timeline.application.dto import TimelineFilterInput
from app.modules.timeline.application.services.timeline_aggregation_service import (
    TimelineAggregationService,
)
from app.modules.timeline.domain.enums import TimelineEventType, TimelineSourceModule
from app.modules.visit.public.dto import VisitSummaryDTO
from tests.unit.modules.timeline.application.fakes import (
    FakeAppointmentQueryPort,
    FakeClinicalNoteQueryPort,
    FakeDoctorReviewQueryPort,
    FakeDocumentQueryPort,
    FakeLabOrderQueryPort,
    FakeLabResultQueryPort,
    FakePatientQueryPort,
    FakePrescriptionQueryPort,
    FakeSOAPNoteQueryPort,
    FakeVisitQueryPort,
    make_allergy_summary,
    make_appointment_summary,
    make_clinical_note_summary,
    make_condition_summary,
    make_doctor_review_summary,
    make_document_summary,
    make_lab_order_summary,
    make_lab_result_summary,
    make_prescription_summary,
    make_soap_note_summary,
    make_visit_summary,
)


def _make_service(
    *,
    appointments: list[AppointmentSummaryDTO] | None = None,
    visits: list[VisitSummaryDTO] | None = None,
    clinical_notes: list[ClinicalNoteSummaryDTO] | None = None,
    soap_notes: list[SOAPNoteSummaryDTO] | None = None,
    prescriptions: list[PrescriptionSummaryDTO] | None = None,
    lab_orders: list[LabOrderSummaryDTO] | None = None,
    lab_results: list[LabResultSummaryDTO] | None = None,
    documents: list[MedicalDocumentSummaryDTO] | None = None,
    patients: list[PatientSummaryDTO] | None = None,
    allergies: list[PatientAllergySummaryDTO] | None = None,
    conditions: list[PatientMedicalConditionSummaryDTO] | None = None,
    reviews: list[DoctorReviewSummaryDTO] | None = None,
) -> TimelineAggregationService:
    return TimelineAggregationService(
        appointment_query_port=FakeAppointmentQueryPort(appointments=appointments),
        visit_query_port=FakeVisitQueryPort(visits=visits),
        clinical_note_query_port=FakeClinicalNoteQueryPort(notes=clinical_notes),
        soap_note_query_port=FakeSOAPNoteQueryPort(soap_notes=soap_notes),
        prescription_query_port=FakePrescriptionQueryPort(prescriptions=prescriptions),
        lab_order_query_port=FakeLabOrderQueryPort(lab_orders=lab_orders),
        lab_result_query_port=FakeLabResultQueryPort(lab_results=lab_results),
        document_query_port=FakeDocumentQueryPort(documents=documents),
        patient_query_port=FakePatientQueryPort(
            patients=patients, allergies=allergies, conditions=conditions
        ),
        doctor_review_query_port=FakeDoctorReviewQueryPort(reviews=reviews),
    )


class TestCollectForPatient:
    async def test_aggregates_events_from_every_source(self) -> None:
        patient_id = uuid4()
        service = _make_service(
            appointments=[make_appointment_summary(patient_id=patient_id)],
            visits=[make_visit_summary(patient_id=patient_id)],
            clinical_notes=[make_clinical_note_summary(patient_id=patient_id)],
            prescriptions=[make_prescription_summary(patient_id=patient_id)],
            lab_orders=[make_lab_order_summary(patient_id=patient_id)],
            lab_results=[make_lab_result_summary(patient_id=patient_id)],
            documents=[make_document_summary(patient_id=patient_id)],
            allergies=[make_allergy_summary(patient_id=patient_id)],
            conditions=[make_condition_summary(patient_id=patient_id)],
            reviews=[make_doctor_review_summary(patient_id=patient_id)],
        )

        events = await service.collect_for_patient(patient_id, filters=TimelineFilterInput())

        event_types = {e.event_type for e in events}
        assert event_types == {
            TimelineEventType.APPOINTMENT,
            TimelineEventType.VISIT,
            TimelineEventType.CLINICAL_NOTE,
            TimelineEventType.PRESCRIPTION,
            TimelineEventType.LAB_ORDER,
            TimelineEventType.LAB_RESULT,
            TimelineEventType.DOCUMENT,
            TimelineEventType.ALLERGY,
            TimelineEventType.MEDICAL_CONDITION,
            TimelineEventType.DOCTOR_REVIEW,
        }
        assert all(e.patient_id == patient_id for e in events)

    async def test_ignores_other_patients_records(self) -> None:
        patient_id = uuid4()
        other_patient_id = uuid4()
        service = _make_service(
            appointments=[
                make_appointment_summary(patient_id=patient_id),
                make_appointment_summary(patient_id=other_patient_id),
            ]
        )

        events = await service.collect_for_patient(patient_id, filters=TimelineFilterInput())

        assert len(events) == 1
        assert events[0].patient_id == patient_id

    async def test_soap_note_fans_out_over_clinical_notes_and_borrows_encounter_datetime(
        self,
    ) -> None:
        patient_id = uuid4()
        clinical_note = make_clinical_note_summary(
            patient_id=patient_id, encounter_datetime=datetime(2026, 3, 1, 10, 0)
        )
        soap_note = make_soap_note_summary(
            clinical_note_id=clinical_note.clinical_note_id, patient_id=patient_id
        )
        service = _make_service(clinical_notes=[clinical_note], soap_notes=[soap_note], patients=[])

        events = await service.collect_for_patient(
            patient_id,
            filters=TimelineFilterInput(event_types=frozenset({TimelineEventType.SOAP_NOTE})),
        )

        assert len(events) == 1
        assert events[0].event_type is TimelineEventType.SOAP_NOTE
        assert events[0].event_datetime == datetime(2026, 3, 1, 10, 0)

    async def test_doctor_review_without_reviewed_at_is_excluded(self) -> None:
        patient_id = uuid4()
        pending_review = make_doctor_review_summary(patient_id=patient_id, reviewed_at=None)
        service = _make_service(reviews=[pending_review])

        events = await service.collect_for_patient(patient_id, filters=TimelineFilterInput())

        assert events == []

    async def test_visit_without_a_derivable_date_is_excluded(self) -> None:
        patient_id = uuid4()
        undated_visit = make_visit_summary(
            patient_id=patient_id, visit_date=None, check_in_time=None
        )
        service = _make_service(visits=[undated_visit])

        events = await service.collect_for_patient(patient_id, filters=TimelineFilterInput())

        assert events == []


class TestSourceModuleFiltering:
    async def test_source_modules_filter_skips_unrequested_ports(self) -> None:
        patient_id = uuid4()
        service = _make_service(
            appointments=[make_appointment_summary(patient_id=patient_id)],
            visits=[make_visit_summary(patient_id=patient_id)],
        )

        events = await service.collect_for_patient(
            patient_id,
            filters=TimelineFilterInput(
                source_modules=frozenset({TimelineSourceModule.APPOINTMENT})
            ),
        )

        assert len(events) == 1
        assert events[0].event_type is TimelineEventType.APPOINTMENT

    async def test_event_types_filter_narrows_to_a_single_type(self) -> None:
        patient_id = uuid4()
        service = _make_service(
            allergies=[make_allergy_summary(patient_id=patient_id)],
            conditions=[make_condition_summary(patient_id=patient_id)],
        )

        events = await service.collect_for_patient(
            patient_id,
            filters=TimelineFilterInput(event_types=frozenset({TimelineEventType.ALLERGY})),
        )

        assert len(events) == 1
        assert events[0].event_type is TimelineEventType.ALLERGY


class TestVisitAndAppointmentFiltering:
    async def test_visit_id_filter_scopes_clinical_notes_via_sql_pushdown(self) -> None:
        patient_id = uuid4()
        visit_id = uuid4()
        other_visit_id = uuid4()
        service = _make_service(
            clinical_notes=[
                make_clinical_note_summary(patient_id=patient_id, visit_id=visit_id),
                make_clinical_note_summary(patient_id=patient_id, visit_id=other_visit_id),
            ]
        )

        events = await service.collect_for_patient(
            patient_id, filters=TimelineFilterInput(visit_id=visit_id)
        )

        assert len(events) == 1
        assert events[0].visit_id == visit_id

    async def test_visit_id_filter_scopes_documents_via_sql_pushdown(self) -> None:
        patient_id = uuid4()
        visit_id = uuid4()
        service = _make_service(
            documents=[
                make_document_summary(patient_id=patient_id, visit_id=visit_id),
                make_document_summary(patient_id=patient_id, visit_id=uuid4()),
            ]
        )

        events = await service.collect_for_patient(
            patient_id, filters=TimelineFilterInput(visit_id=visit_id)
        )

        assert len(events) == 1

    async def test_visit_id_filter_also_narrows_sources_without_sql_pushdown(self) -> None:
        """`Prescription` has no visit-scoped fetch — the final in-memory
        filter pass still narrows it down."""
        patient_id = uuid4()
        visit_id = uuid4()
        service = _make_service(
            prescriptions=[
                make_prescription_summary(patient_id=patient_id, visit_id=visit_id),
                make_prescription_summary(patient_id=patient_id, visit_id=uuid4()),
            ]
        )

        events = await service.collect_for_patient(
            patient_id, filters=TimelineFilterInput(visit_id=visit_id)
        )

        assert len(events) == 1
        assert events[0].visit_id == visit_id

    async def test_appointment_id_filter_scopes_documents_via_sql_pushdown(self) -> None:
        patient_id = uuid4()
        appointment_id = uuid4()
        service = _make_service(
            documents=[
                make_document_summary(patient_id=patient_id, appointment_id=appointment_id),
                make_document_summary(patient_id=patient_id, appointment_id=uuid4()),
            ]
        )

        events = await service.collect_for_patient(
            patient_id, filters=TimelineFilterInput(appointment_id=appointment_id)
        )

        assert len(events) == 1
