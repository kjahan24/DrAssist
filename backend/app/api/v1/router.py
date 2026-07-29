"""v1 API route aggregator.

Aggregates each module's own `api/router.py`. Neither module's router
registers endpoints itself yet (see each module's `container.py` for why)
— they're wired in now so both are present in the app/OpenAPI schema from
day one, and so future endpoint modules only need to register into their
own `api/router.py`, not touch this file again.
"""

from fastapi import APIRouter

from app.modules.authentication.api.router import router as authentication_router
from app.modules.chief_complaints.api.router import router as chief_complaints_router
from app.modules.diagnosis.api.router import router as diagnosis_router
from app.modules.doctor.api.router import router as doctor_router
from app.modules.organization.api.router import router as organization_router
from app.modules.patient.api.router import router as patient_router
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
