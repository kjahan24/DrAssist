"""v1 API route aggregator.

Aggregates each module's own `api/router.py`. Neither module's router
registers endpoints itself yet (see each module's `container.py` for why)
— they're wired in now so both are present in the app/OpenAPI schema from
day one, and so future endpoint modules only need to register into their
own `api/router.py`, not touch this file again.
"""

from fastapi import APIRouter

from app.modules.attachments.api.router import router as attachments_router
from app.modules.authentication.api.router import router as authentication_router
from app.modules.chief_complaints.api.router import router as chief_complaints_router
from app.modules.clinical_notes.api.router import router as clinical_notes_router
from app.modules.clinical_reasoning.api.router import router as clinical_reasoning_router
from app.modules.diagnosis.api.router import router as diagnosis_router
from app.modules.differential_diagnosis.api.router import (
    router as differential_diagnosis_router,
)
from app.modules.doctor.api.router import router as doctor_router
from app.modules.lab_orders.api.router import router as lab_orders_router
from app.modules.lab_results.api.router import router as lab_results_router
from app.modules.organization.api.router import router as organization_router
from app.modules.patient.api.router import router as patient_router
from app.modules.prescriptions.api.router import router as prescriptions_router
from app.modules.procedures.api.router import router as procedures_router
from app.modules.soap_notes.api.router import router as soap_notes_router
from app.modules.visit.api.router import router as visit_router
from app.modules.vital_signs.api.router import router as vital_signs_router

api_router = APIRouter()
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
