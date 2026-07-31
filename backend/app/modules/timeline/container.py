"""Module composition root.

The one place `TimelineQueryPort` gets bound to its concrete
implementation (`TimelineFacade`). Any future module's
`api/dependencies.py` calls `build_timeline_facade(session)` rather than
constructing `TimelineFacade` (or `TimelineAggregationService`/
`TimelineQueryService`) directly.

Scope note — this task builds the Personal Health Timeline module's
**foundation**: a pure read-side aggregation layer over ten existing
modules (Appointment, Visit, Clinical Notes, SOAP Notes, Prescriptions,
Lab Orders, Lab Results, Documents, Patient — for Allergies/Medical
Conditions — and Doctor Review), each depended on exclusively through
its own public port, built via its own `build_..._facade(session)`
composition root — the same "compose N peer facades in one service"
pattern `app.modules.doctor_review.api.dependencies` and
`app.modules.patient_history.api.dependencies` already establish.

There is deliberately **no** `infrastructure/` package and **no**
database table: `TimelineEventDTO` is generated dynamically, on every
request, from each peer module's own already-persisted data — this task
explicitly excludes storing (or duplicating) timeline events, and the
verification checklist's `alembic upgrade head`/`downgrade -1` round-trip
has nothing of this module's own to apply (no new migration is part of
this task).

This module also does **not** build a frontend, authentication,
authorization middleware, or background jobs (per this task's explicit
exclusions), and does not modify the Authentication, Organization, or
Doctor modules or their tables. It makes two small, additive, and
individually-justified changes to two *previous* modules' public ports
(never their domain/schema) — see `app.modules.patient.public.interfaces
.PatientQueryPort`'s and `app.modules.visit.public.interfaces
.VisitQueryPort`'s own docstrings for the full reasoning behind each.

Vaccinations, Wearable Devices, and AI Insights are reserved,
future-ready placeholders on `domain/enums.py` only — no source module
for any of them exists yet, so `TimelineAggregationService` never
produces an event of one of those types. Patient Portal, Personal Health
Dashboard, Family/Caregiver Access, Medical Community, AI Health
Summary, Timeline PDF Export, Mobile App Timeline, and FHIR APIs are
expected to become their own consumers of `TimelineQueryPort` — nothing
about this module's shape needs to change to support them: `TimelineEventDTO`
already carries everything a rendering/export/FHIR-mapping layer would
need (`event_type`, `source_module`, `reference_id` to look up full
detail in the owning module, `icon_key`/`color_key` for presentation,
and `metadata` for anything source-specific).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.appointment.container import build_appointment_facade
from app.modules.clinical_notes.container import build_clinical_note_facade
from app.modules.doctor_review.container import build_doctor_review_facade
from app.modules.documents.container import build_document_facade
from app.modules.lab_orders.container import build_lab_order_facade
from app.modules.lab_results.container import build_lab_result_facade
from app.modules.patient.container import build_patient_facade
from app.modules.prescriptions.container import build_prescription_facade
from app.modules.soap_notes.container import build_soap_note_facade
from app.modules.timeline.application.services.timeline_aggregation_service import (
    TimelineAggregationService,
)
from app.modules.timeline.application.services.timeline_query_service import (
    TimelineQueryService,
)
from app.modules.timeline.public.facade import TimelineFacade
from app.modules.visit.container import build_visit_facade


def build_timeline_facade(session: AsyncSession) -> TimelineFacade:
    """Construct a `TimelineFacade` wired to `session`.

    Called once per request (or per Celery task) — every peer facade it
    builds shares `session`, so every read within one aggregation call
    participates in the same transaction as the rest of that request's
    work.
    """
    appointment_facade = build_appointment_facade(session)
    visit_facade = build_visit_facade(session)
    clinical_note_facade = build_clinical_note_facade(session)
    soap_note_facade = build_soap_note_facade(session)
    prescription_facade = build_prescription_facade(session)
    lab_order_facade = build_lab_order_facade(session)
    lab_result_facade = build_lab_result_facade(session)
    document_facade = build_document_facade(session)
    patient_facade = build_patient_facade(session)
    doctor_review_facade = build_doctor_review_facade(session)

    aggregation_service = TimelineAggregationService(
        appointment_query_port=appointment_facade,
        visit_query_port=visit_facade,
        clinical_note_query_port=clinical_note_facade,
        soap_note_query_port=soap_note_facade,
        prescription_query_port=prescription_facade,
        lab_order_query_port=lab_order_facade,
        lab_result_query_port=lab_result_facade,
        document_query_port=document_facade,
        patient_query_port=patient_facade,
        doctor_review_query_port=doctor_review_facade,
    )
    query_service = TimelineQueryService(
        aggregation_service=aggregation_service,
        patient_query_port=patient_facade,
        visit_query_port=visit_facade,
        appointment_query_port=appointment_facade,
    )

    return TimelineFacade(query_service=query_service)
