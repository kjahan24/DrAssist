"""v1 API route aggregator.

Aggregates each module's own `api/router.py`. Neither module's router
registers endpoints itself yet (see each module's `container.py` for why)
— they're wired in now so both are present in the app/OpenAPI schema from
day one, and so future endpoint modules only need to register into their
own `api/router.py`, not touch this file again.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.modules.appointment.api.router import router as appointment_router
from app.modules.attachments.api.router import router as attachments_router
from app.modules.audit_log.api.router import router as audit_log_router
from app.modules.authentication.api.router import router as authentication_router
from app.modules.chief_complaints.api.router import router as chief_complaints_router
from app.modules.clinical_notes.api.router import router as clinical_notes_router
from app.modules.clinical_reasoning.api.router import router as clinical_reasoning_router
from app.modules.diagnosis.api.router import router as diagnosis_router
from app.modules.differential_diagnosis.api.router import (
    router as differential_diagnosis_router,
)
from app.modules.doctor.api.router import router as doctor_router
from app.modules.doctor_review.api.router import router as doctor_review_router
from app.modules.documents.api.router import router as documents_router
from app.modules.family_access.api.router import router as family_access_router
from app.modules.icd10_coding.api.router import router as icd10_coding_router
from app.modules.lab_orders.api.router import router as lab_orders_router
from app.modules.lab_results.api.router import router as lab_results_router
from app.modules.notification.api.router import router as notification_router
from app.modules.organization.api.router import router as organization_router
from app.modules.patient.api.router import router as patient_router
from app.modules.patient_history.api.router import router as patient_history_router
from app.modules.prescriptions.api.router import router as prescriptions_router
from app.modules.procedures.api.router import router as procedures_router
from app.modules.schedule.api.router import router as schedule_router
from app.modules.soap_notes.api.router import router as soap_notes_router
from app.modules.timeline.api.router import router as timeline_router
from app.modules.visit.api.router import router as visit_router
from app.modules.vital_signs.api.router import router as vital_signs_router

api_router = APIRouter()
# No prefix: `health.py`'s own routes are already "/health" and
# "/health/db" (so a load balancer can probe them without depending on
# api_version), unlike every module below, whose router paths are
# relative and need their own resource-name prefix.
api_router.include_router(health_router, tags=["health"])
api_router.include_router(authentication_router, prefix="/auth", tags=["authentication"])
api_router.include_router(organization_router, prefix="/organizations", tags=["organization"])
api_router.include_router(doctor_router, prefix="/doctors", tags=["doctor"])
api_router.include_router(patient_router, prefix="/patients", tags=["patient"])
api_router.include_router(visit_router, prefix="/visits", tags=["visit"])
api_router.include_router(vital_signs_router, prefix="/vital-signs", tags=["vital-signs"])
api_router.include_router(
    chief_complaints_router, prefix="/chief-complaints", tags=["chief-complaints"]
)
api_router.include_router(diagnosis_router, prefix="/diagnoses", tags=["diagnosis"])
api_router.include_router(procedures_router, prefix="/procedures", tags=["procedures"])
api_router.include_router(attachments_router, prefix="/attachments", tags=["attachments"])
api_router.include_router(clinical_notes_router, prefix="/clinical-notes", tags=["clinical-notes"])
api_router.include_router(soap_notes_router, prefix="/soap-notes", tags=["soap-notes"])
api_router.include_router(prescriptions_router, prefix="/prescriptions", tags=["prescriptions"])
api_router.include_router(lab_orders_router, prefix="/lab-orders", tags=["lab-orders"])
api_router.include_router(lab_results_router, prefix="/lab-results", tags=["lab-results"])
api_router.include_router(
    clinical_reasoning_router, prefix="/clinical-reasoning", tags=["clinical-reasoning"]
)
api_router.include_router(
    differential_diagnosis_router,
    prefix="/differential-diagnoses",
    tags=["differential-diagnosis"],
)
api_router.include_router(icd10_coding_router, prefix="/icd10-codes", tags=["icd10-coding"])
api_router.include_router(doctor_review_router, prefix="/doctor-reviews", tags=["doctor-review"])
api_router.include_router(
    patient_history_router, prefix="/patient-history", tags=["patient-history"]
)
api_router.include_router(appointment_router, prefix="/appointments", tags=["appointment"])
api_router.include_router(schedule_router, prefix="/schedule", tags=["schedule"])
api_router.include_router(notification_router, prefix="/notifications", tags=["notification"])
api_router.include_router(audit_log_router, prefix="/audit-logs", tags=["audit-log"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(timeline_router, prefix="/timeline", tags=["timeline"])
api_router.include_router(family_access_router, prefix="/family-access", tags=["family-access"])
