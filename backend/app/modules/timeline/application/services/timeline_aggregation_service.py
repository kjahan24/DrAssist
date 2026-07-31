"""`TimelineAggregationService` — fans out to the 10 peer modules'
public query ports for one patient, maps each result into a unified
`TimelineEventDTO`, and returns the merged (but not yet sorted, paginated,
or date/category-filtered — see `TimelineQueryService`) list.

Mirrors the "compose N peer modules' public ports in one service"
composition pattern `app.modules.patient_history.application.services
.patient_history_reference_validator.PatientHistoryReferenceValidator`
and `app.modules.doctor_review.application.services
.doctor_review_consistency_service.DoctorReviewConsistencyService`
already establish for this codebase — one query port per peer module,
injected as constructor kwargs, each built via its own
`build_..._facade(session)` composition root in `api/dependencies.py`.

Performance ("efficient aggregation", "avoid N+1 queries" — see this
task's own Performance section): `event_type`/`source_module` filters
skip calling a peer module's port entirely when none of its event types
were requested — the real optimization available here, since each
source lives in its own module/aggregate boundary and there is no SQL
join across them by design (see `docs/backend-architecture
/03_module_architecture.md`). Where a peer module already exposes a
narrower, SQL-filtered fetch (`ClinicalNoteQueryPort
.list_clinical_notes_for_visit`, `DocumentQueryPort
.list_documents_for_visit`/`list_documents_for_appointment`), a
`visit_id`/`appointment_id` filter is pushed down to it instead of
fetching every one of the patient's records and discarding most in
Python — "SQL-level filtering where possible", not everywhere, since
most peer ports only support patient-scoped fetches today.

SOAP Notes has no patient- or visit-scoped list method at all (`SOAPNote`
is a strict 1:1 child of `ClinicalNote`, keyed only by
`clinical_note_id`) — rather than adding one (which would mean modifying
a previous module without an existing read path one layer down to
expose, unlike the Patient/Visit additions this task's `container.py`
documents), this collects it via a bounded fan-out over the clinical
notes already fetched for this same patient/visit: one
`get_soap_note_summary(clinical_note_id)` call per note, which is the
same shape every other per-source fetch below already has relative to a
hypothetical single joined query.

Doctor Review events are only produced once `reviewed_at` is set — a
`Pending` review has no completion timestamp to place it on a
chronological timeline (see `application/dto.py`'s own field list; there
is no `created_at` on `DoctorReviewSummaryDTO`).
"""

from datetime import UTC, datetime, time
from uuid import NAMESPACE_URL, UUID, uuid5

from app.modules.appointment.public.dto import AppointmentSummaryDTO
from app.modules.appointment.public.interfaces import AppointmentQueryPort
from app.modules.clinical_notes.public.dto import ClinicalNoteSummaryDTO
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.doctor_review.public.dto import DoctorReviewSummaryDTO
from app.modules.doctor_review.public.interfaces import DoctorReviewQueryPort
from app.modules.documents.public.dto import MedicalDocumentSummaryDTO
from app.modules.documents.public.interfaces import DocumentQueryPort
from app.modules.lab_orders.public.dto import LabOrderSummaryDTO
from app.modules.lab_orders.public.interfaces import LabOrderQueryPort
from app.modules.lab_results.public.dto import LabResultSummaryDTO
from app.modules.lab_results.public.interfaces import LabResultQueryPort
from app.modules.patient.public.dto import (
    PatientAllergySummaryDTO,
    PatientMedicalConditionSummaryDTO,
)
from app.modules.patient.public.interfaces import PatientQueryPort
from app.modules.prescriptions.public.dto import PrescriptionSummaryDTO
from app.modules.prescriptions.public.interfaces import PrescriptionQueryPort
from app.modules.soap_notes.public.dto import SOAPNoteSummaryDTO
from app.modules.soap_notes.public.interfaces import SOAPNoteQueryPort
from app.modules.timeline.application.dto import TimelineEventDTO, TimelineFilterInput
from app.modules.timeline.domain.enums import (
    TimelineEventCategory,
    TimelineEventType,
    TimelineSourceModule,
)
from app.modules.visit.public.dto import VisitSummaryDTO
from app.modules.visit.public.interfaces import VisitQueryPort

_TIMELINE_NAMESPACE = uuid5(NAMESPACE_URL, "https://drassist.internal/timeline")

_EVENT_TYPE_SOURCE: dict[TimelineEventType, TimelineSourceModule] = {
    TimelineEventType.APPOINTMENT: TimelineSourceModule.APPOINTMENT,
    TimelineEventType.VISIT: TimelineSourceModule.VISIT,
    TimelineEventType.CLINICAL_NOTE: TimelineSourceModule.CLINICAL_NOTES,
    TimelineEventType.SOAP_NOTE: TimelineSourceModule.SOAP_NOTES,
    TimelineEventType.PRESCRIPTION: TimelineSourceModule.PRESCRIPTIONS,
    TimelineEventType.LAB_ORDER: TimelineSourceModule.LAB_ORDERS,
    TimelineEventType.LAB_RESULT: TimelineSourceModule.LAB_RESULTS,
    TimelineEventType.DOCUMENT: TimelineSourceModule.DOCUMENTS,
    TimelineEventType.ALLERGY: TimelineSourceModule.PATIENT,
    TimelineEventType.MEDICAL_CONDITION: TimelineSourceModule.PATIENT,
    TimelineEventType.DOCTOR_REVIEW: TimelineSourceModule.DOCTOR_REVIEW,
}
_IMPLEMENTED_TYPES = frozenset(_EVENT_TYPE_SOURCE)
_IMPLEMENTED_SOURCES = frozenset(_EVENT_TYPE_SOURCE.values())

_EVENT_CATEGORY: dict[TimelineEventType, TimelineEventCategory] = {
    TimelineEventType.APPOINTMENT: TimelineEventCategory.SCHEDULING,
    TimelineEventType.VISIT: TimelineEventCategory.SCHEDULING,
    TimelineEventType.CLINICAL_NOTE: TimelineEventCategory.CLINICAL_DOCUMENTATION,
    TimelineEventType.SOAP_NOTE: TimelineEventCategory.CLINICAL_DOCUMENTATION,
    TimelineEventType.PRESCRIPTION: TimelineEventCategory.MEDICATION,
    TimelineEventType.LAB_ORDER: TimelineEventCategory.DIAGNOSTICS,
    TimelineEventType.LAB_RESULT: TimelineEventCategory.DIAGNOSTICS,
    TimelineEventType.DOCUMENT: TimelineEventCategory.DOCUMENT,
    TimelineEventType.ALLERGY: TimelineEventCategory.HEALTH_RECORD,
    TimelineEventType.MEDICAL_CONDITION: TimelineEventCategory.HEALTH_RECORD,
    TimelineEventType.DOCTOR_REVIEW: TimelineEventCategory.REVIEW,
}

_ICON_KEYS: dict[TimelineEventType, str] = {
    TimelineEventType.APPOINTMENT: "calendar",
    TimelineEventType.VISIT: "stethoscope",
    TimelineEventType.CLINICAL_NOTE: "clipboard-text",
    TimelineEventType.SOAP_NOTE: "clipboard-list",
    TimelineEventType.PRESCRIPTION: "pill",
    TimelineEventType.LAB_ORDER: "flask-conical",
    TimelineEventType.LAB_RESULT: "flask",
    TimelineEventType.DOCUMENT: "file-text",
    TimelineEventType.ALLERGY: "alert-triangle",
    TimelineEventType.MEDICAL_CONDITION: "activity",
    TimelineEventType.DOCTOR_REVIEW: "check-circle",
}

_COLOR_KEYS: dict[TimelineEventType, str] = {
    TimelineEventType.APPOINTMENT: "blue",
    TimelineEventType.VISIT: "teal",
    TimelineEventType.CLINICAL_NOTE: "indigo",
    TimelineEventType.SOAP_NOTE: "purple",
    TimelineEventType.PRESCRIPTION: "green",
    TimelineEventType.LAB_ORDER: "amber",
    TimelineEventType.LAB_RESULT: "orange",
    TimelineEventType.DOCUMENT: "slate",
    TimelineEventType.ALLERGY: "red",
    TimelineEventType.MEDICAL_CONDITION: "rose",
    TimelineEventType.DOCTOR_REVIEW: "emerald",
}


class TimelineAggregationService:
    def __init__(
        self,
        *,
        appointment_query_port: AppointmentQueryPort,
        visit_query_port: VisitQueryPort,
        clinical_note_query_port: ClinicalNoteQueryPort,
        soap_note_query_port: SOAPNoteQueryPort,
        prescription_query_port: PrescriptionQueryPort,
        lab_order_query_port: LabOrderQueryPort,
        lab_result_query_port: LabResultQueryPort,
        document_query_port: DocumentQueryPort,
        patient_query_port: PatientQueryPort,
        doctor_review_query_port: DoctorReviewQueryPort,
    ) -> None:
        self._appointments = appointment_query_port
        self._visits = visit_query_port
        self._clinical_notes = clinical_note_query_port
        self._soap_notes = soap_note_query_port
        self._prescriptions = prescription_query_port
        self._lab_orders = lab_order_query_port
        self._lab_results = lab_result_query_port
        self._documents = document_query_port
        self._patients = patient_query_port
        self._doctor_reviews = doctor_review_query_port

    async def collect_for_patient(
        self, patient_id: UUID, *, filters: TimelineFilterInput
    ) -> list[TimelineEventDTO]:
        wanted_sources = _resolve_wanted_sources(filters)
        wanted_types = _resolve_wanted_types(filters)
        events: list[TimelineEventDTO] = []

        if TimelineSourceModule.APPOINTMENT in wanted_sources:
            for appointment in await self._appointments.list_appointments_for_patient(patient_id):
                events.append(_map_appointment(appointment))

        if TimelineSourceModule.VISIT in wanted_sources:
            for visit in await self._visits.list_visits_for_patient(patient_id):
                event = _map_visit(visit)
                if event is not None:
                    events.append(event)

        clinical_notes: list[ClinicalNoteSummaryDTO] | None = None
        needs_clinical_notes = (
            TimelineSourceModule.CLINICAL_NOTES in wanted_sources
            or TimelineEventType.SOAP_NOTE in wanted_types
        )
        if needs_clinical_notes:
            clinical_notes = (
                await self._clinical_notes.list_clinical_notes_for_visit(filters.visit_id)
                if filters.visit_id is not None
                else await self._clinical_notes.list_clinical_notes_for_patient(patient_id)
            )
            if TimelineSourceModule.CLINICAL_NOTES in wanted_sources:
                events.extend(_map_clinical_note(note) for note in clinical_notes)

        if TimelineEventType.SOAP_NOTE in wanted_types:
            for note in clinical_notes or []:
                soap_note = await self._soap_notes.get_soap_note_summary(note.clinical_note_id)
                if soap_note is not None:
                    events.append(
                        _map_soap_note(
                            soap_note,
                            note_number=note.note_number,
                            encounter_datetime=note.encounter_datetime,
                        )
                    )

        if TimelineSourceModule.PRESCRIPTIONS in wanted_sources:
            prescriptions = await self._prescriptions.list_prescriptions_for_patient(patient_id)
            events.extend(_map_prescription(p) for p in prescriptions)

        if TimelineSourceModule.LAB_ORDERS in wanted_sources:
            lab_orders = await self._lab_orders.list_lab_orders_for_patient(patient_id)
            events.extend(_map_lab_order(o) for o in lab_orders)

        if TimelineSourceModule.LAB_RESULTS in wanted_sources:
            lab_results = await self._lab_results.list_lab_results_for_patient(patient_id)
            events.extend(_map_lab_result(r) for r in lab_results)

        if TimelineSourceModule.DOCUMENTS in wanted_sources:
            if filters.visit_id is not None:
                documents = await self._documents.list_documents_for_visit(filters.visit_id)
            elif filters.appointment_id is not None:
                documents = await self._documents.list_documents_for_appointment(
                    filters.appointment_id
                )
            else:
                documents = await self._documents.list_documents_for_patient(patient_id)
            events.extend(_map_document(d) for d in documents)

        if TimelineEventType.ALLERGY in wanted_types:
            allergies = await self._patients.list_allergies_for_patient(patient_id)
            events.extend(e for a in allergies if (e := _map_allergy(a)) is not None)

        if TimelineEventType.MEDICAL_CONDITION in wanted_types:
            conditions = await self._patients.list_medical_conditions_for_patient(patient_id)
            events.extend(_map_condition(c) for c in conditions)

        if TimelineSourceModule.DOCTOR_REVIEW in wanted_sources:
            reviews = await self._doctor_reviews.list_doctor_reviews_for_patient(patient_id)
            events.extend(_map_doctor_review(r) for r in reviews if r.reviewed_at is not None)

        if filters.visit_id is not None:
            events = [e for e in events if e.visit_id == filters.visit_id]
        if filters.appointment_id is not None:
            events = [e for e in events if e.appointment_id == filters.appointment_id]

        return events


def _resolve_wanted_sources(filters: TimelineFilterInput) -> frozenset[TimelineSourceModule]:
    if filters.source_modules is not None:
        return filters.source_modules
    if filters.event_types is not None:
        return frozenset(
            _EVENT_TYPE_SOURCE[t] for t in filters.event_types if t in _EVENT_TYPE_SOURCE
        )
    return _IMPLEMENTED_SOURCES


def _resolve_wanted_types(filters: TimelineFilterInput) -> frozenset[TimelineEventType]:
    if filters.event_types is not None:
        return filters.event_types
    return _IMPLEMENTED_TYPES


def _make_event_id(event_type: TimelineEventType, reference_id: UUID) -> UUID:
    """Deterministic, stable, and reproducible across requests (this
    module generates nothing persisted — see `container.py`'s scope
    note) — yet distinct in form from `reference_id`, leaving room for a
    future record producing more than one timeline event without an
    `event_id` collision."""
    return uuid5(_TIMELINE_NAMESPACE, f"{event_type.value}:{reference_id}")


def _map_appointment(appointment: AppointmentSummaryDTO) -> TimelineEventDTO:
    event_type = TimelineEventType.APPOINTMENT
    event_datetime = datetime.combine(
        appointment.appointment_date, appointment.start_time, tzinfo=UTC
    )
    label = appointment.appointment_type.value.replace("_", " ").title()
    return TimelineEventDTO(
        event_id=_make_event_id(event_type, appointment.appointment_id),
        event_type=event_type,
        event_category=_EVENT_CATEGORY[event_type],
        patient_id=appointment.patient_id,
        organization_id=appointment.organization_id,
        visit_id=appointment.visit_id,
        appointment_id=appointment.appointment_id,
        reference_id=appointment.appointment_id,
        title=f"Appointment — {label}",
        summary=appointment.reason_for_visit,
        event_datetime=event_datetime,
        created_by=appointment.booked_by_user_id,
        source_module=TimelineSourceModule.APPOINTMENT,
        icon_key=_ICON_KEYS[event_type],
        color_key=_COLOR_KEYS[event_type],
        metadata={
            "status": appointment.status.value,
            "appointment_type": appointment.appointment_type.value,
        },
    )


def _map_visit(visit: VisitSummaryDTO) -> TimelineEventDTO | None:
    event_type = TimelineEventType.VISIT
    event_datetime = visit.check_in_time or (
        datetime.combine(visit.visit_date, time.min, tzinfo=UTC) if visit.visit_date else None
    )
    if event_datetime is None:
        return None
    return TimelineEventDTO(
        event_id=_make_event_id(event_type, visit.visit_id),
        event_type=event_type,
        event_category=_EVENT_CATEGORY[event_type],
        patient_id=visit.patient_id,
        organization_id=visit.organization_id,
        visit_id=visit.visit_id,
        appointment_id=visit.appointment_id,
        reference_id=visit.visit_id,
        title=f"Visit #{visit.visit_number}",
        summary=visit.chief_complaint_summary or visit.reason_for_visit,
        event_datetime=event_datetime,
        created_by=visit.doctor_id,
        source_module=TimelineSourceModule.VISIT,
        icon_key=_ICON_KEYS[event_type],
        color_key=_COLOR_KEYS[event_type],
        metadata={
            "visit_status": visit.visit_status.value,
            "visit_type": visit.visit_type.value if visit.visit_type else None,
        },
    )


def _map_clinical_note(note: ClinicalNoteSummaryDTO) -> TimelineEventDTO:
    event_type = TimelineEventType.CLINICAL_NOTE
    return TimelineEventDTO(
        event_id=_make_event_id(event_type, note.clinical_note_id),
        event_type=event_type,
        event_category=_EVENT_CATEGORY[event_type],
        patient_id=note.patient_id,
        organization_id=note.organization_id,
        visit_id=note.visit_id,
        appointment_id=None,
        reference_id=note.clinical_note_id,
        title=f"Clinical Note #{note.note_number}",
        summary=note.chief_complaint_summary or note.assessment_summary,
        event_datetime=note.encounter_datetime,
        created_by=note.signed_by or note.doctor_id,
        source_module=TimelineSourceModule.CLINICAL_NOTES,
        icon_key=_ICON_KEYS[event_type],
        color_key=_COLOR_KEYS[event_type],
        metadata={"status": note.status.value, "note_type": note.note_type.value},
    )


def _map_soap_note(
    soap_note: SOAPNoteSummaryDTO, *, note_number: str, encounter_datetime: datetime
) -> TimelineEventDTO:
    """`SOAPNoteSummaryDTO` has no date field of its own (see this
    module's own docstring) — `event_datetime`/`title` borrow from the
    parent `ClinicalNoteSummaryDTO` the caller already fetched it
    through."""
    event_type = TimelineEventType.SOAP_NOTE
    return TimelineEventDTO(
        event_id=_make_event_id(event_type, soap_note.soap_note_id),
        event_type=event_type,
        event_category=_EVENT_CATEGORY[event_type],
        patient_id=soap_note.patient_id,
        organization_id=soap_note.organization_id,
        visit_id=soap_note.visit_id,
        appointment_id=None,
        reference_id=soap_note.soap_note_id,
        title=f"SOAP Note — {note_number}",
        summary=soap_note.chief_complaint or soap_note.assessment,
        event_datetime=encounter_datetime,
        created_by=soap_note.doctor_id,
        source_module=TimelineSourceModule.SOAP_NOTES,
        icon_key=_ICON_KEYS[event_type],
        color_key=_COLOR_KEYS[event_type],
        metadata={"clinical_note_id": str(soap_note.clinical_note_id)},
    )


def _map_prescription(prescription: PrescriptionSummaryDTO) -> TimelineEventDTO:
    event_type = TimelineEventType.PRESCRIPTION
    return TimelineEventDTO(
        event_id=_make_event_id(event_type, prescription.prescription_id),
        event_type=event_type,
        event_category=_EVENT_CATEGORY[event_type],
        patient_id=prescription.patient_id,
        organization_id=prescription.organization_id,
        visit_id=prescription.visit_id,
        appointment_id=None,
        reference_id=prescription.prescription_id,
        title=f"Prescription #{prescription.prescription_number}",
        summary=prescription.notes
        or (f"{len(prescription.items)} medication(s)" if prescription.items else None),
        event_datetime=datetime.combine(prescription.prescription_date, time.min, tzinfo=UTC),
        created_by=prescription.doctor_id,
        source_module=TimelineSourceModule.PRESCRIPTIONS,
        icon_key=_ICON_KEYS[event_type],
        color_key=_COLOR_KEYS[event_type],
        metadata={"status": prescription.status.value, "item_count": len(prescription.items)},
    )


def _map_lab_order(lab_order: LabOrderSummaryDTO) -> TimelineEventDTO:
    event_type = TimelineEventType.LAB_ORDER
    return TimelineEventDTO(
        event_id=_make_event_id(event_type, lab_order.lab_order_id),
        event_type=event_type,
        event_category=_EVENT_CATEGORY[event_type],
        patient_id=lab_order.patient_id,
        organization_id=lab_order.organization_id,
        visit_id=lab_order.visit_id,
        appointment_id=None,
        reference_id=lab_order.lab_order_id,
        title=f"Lab Order #{lab_order.order_number}",
        summary=lab_order.clinical_information or lab_order.notes,
        event_datetime=lab_order.ordered_at,
        created_by=lab_order.doctor_id,
        source_module=TimelineSourceModule.LAB_ORDERS,
        icon_key=_ICON_KEYS[event_type],
        color_key=_COLOR_KEYS[event_type],
        metadata={"status": lab_order.status.value, "priority": lab_order.priority.value},
    )


def _map_lab_result(lab_result: LabResultSummaryDTO) -> TimelineEventDTO:
    event_type = TimelineEventType.LAB_RESULT
    return TimelineEventDTO(
        event_id=_make_event_id(event_type, lab_result.lab_result_id),
        event_type=event_type,
        event_category=_EVENT_CATEGORY[event_type],
        patient_id=lab_result.patient_id,
        organization_id=lab_result.organization_id,
        visit_id=lab_result.visit_id,
        appointment_id=None,
        reference_id=lab_result.lab_result_id,
        title=f"Lab Result #{lab_result.result_number}",
        summary=lab_result.comments or lab_result.laboratory_name,
        event_datetime=lab_result.reported_at,
        created_by=lab_result.doctor_id,
        source_module=TimelineSourceModule.LAB_RESULTS,
        icon_key=_ICON_KEYS[event_type],
        color_key=_COLOR_KEYS[event_type],
        metadata={"status": lab_result.status.value, "item_count": len(lab_result.items)},
    )


def _map_document(document: MedicalDocumentSummaryDTO) -> TimelineEventDTO:
    event_type = TimelineEventType.DOCUMENT
    return TimelineEventDTO(
        event_id=_make_event_id(event_type, document.document_id),
        event_type=event_type,
        event_category=_EVENT_CATEGORY[event_type],
        patient_id=document.patient_id,
        organization_id=document.organization_id,
        visit_id=document.visit_id,
        appointment_id=document.appointment_id,
        reference_id=document.document_id,
        title=document.title,
        summary=document.description,
        event_datetime=document.uploaded_at,
        created_by=document.uploaded_by_user_id,
        source_module=TimelineSourceModule.DOCUMENTS,
        icon_key=_ICON_KEYS[event_type],
        color_key=_COLOR_KEYS[event_type],
        metadata={"status": document.status.value, "category": document.category.value},
    )


def _map_allergy(allergy: PatientAllergySummaryDTO) -> TimelineEventDTO | None:
    """No `event_datetime` can be derived when both `onset_date` and
    `verified_date` are unset — same "skip rather than invent a
    timestamp" choice as `_map_visit`."""
    event_type = TimelineEventType.ALLERGY
    onset = allergy.onset_date or allergy.verified_date
    if onset is None:
        return None
    return TimelineEventDTO(
        event_id=_make_event_id(event_type, allergy.allergy_id),
        event_type=event_type,
        event_category=_EVENT_CATEGORY[event_type],
        patient_id=allergy.patient_id,
        organization_id=allergy.organization_id,
        visit_id=None,
        appointment_id=None,
        reference_id=allergy.allergy_id,
        title=f"Allergy — {allergy.allergen_name}",
        summary=allergy.reaction,
        event_datetime=datetime.combine(onset, time.min, tzinfo=UTC),
        created_by=allergy.verified_by,
        source_module=TimelineSourceModule.PATIENT,
        icon_key=_ICON_KEYS[event_type],
        color_key=_COLOR_KEYS[event_type],
        metadata={"allergy_type": allergy.allergy_type.value, "severity": allergy.severity.value},
    )


def _map_condition(condition: PatientMedicalConditionSummaryDTO) -> TimelineEventDTO:
    event_type = TimelineEventType.MEDICAL_CONDITION
    return TimelineEventDTO(
        event_id=_make_event_id(event_type, condition.condition_id),
        event_type=event_type,
        event_category=_EVENT_CATEGORY[event_type],
        patient_id=condition.patient_id,
        organization_id=condition.organization_id,
        visit_id=None,
        appointment_id=None,
        reference_id=condition.condition_id,
        title=f"Medical Condition — {condition.condition_name}",
        summary=condition.notes,
        event_datetime=datetime.combine(condition.diagnosis_date, time.min, tzinfo=UTC),
        created_by=condition.diagnosed_by,
        source_module=TimelineSourceModule.PATIENT,
        icon_key=_ICON_KEYS[event_type],
        color_key=_COLOR_KEYS[event_type],
        metadata={"severity": condition.severity.value, "is_chronic": condition.is_chronic},
    )


def _map_doctor_review(review: DoctorReviewSummaryDTO) -> TimelineEventDTO:
    event_type = TimelineEventType.DOCTOR_REVIEW
    assert review.reviewed_at is not None  # caller only passes completed reviews
    return TimelineEventDTO(
        event_id=_make_event_id(event_type, review.doctor_review_id),
        event_type=event_type,
        event_category=_EVENT_CATEGORY[event_type],
        patient_id=review.patient_id,
        organization_id=review.organization_id,
        visit_id=review.visit_id,
        appointment_id=None,
        reference_id=review.doctor_review_id,
        title=f"Doctor Review — {review.review_status.value.title()}",
        summary=review.review_comment,
        event_datetime=review.reviewed_at,
        created_by=review.doctor_id,
        source_module=TimelineSourceModule.DOCTOR_REVIEW,
        icon_key=_ICON_KEYS[event_type],
        color_key=_COLOR_KEYS[event_type],
        metadata={"review_status": review.review_status.value},
    )
