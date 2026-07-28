"""v1 API route aggregator.

Aggregates each module's own `api/router.py`. Neither module's router
registers endpoints itself yet (see each module's `container.py` for why)
— they're wired in now so both are present in the app/OpenAPI schema from
day one, and so future endpoint modules only need to register into their
own `api/router.py`, not touch this file again.
"""

from fastapi import APIRouter

from app.modules.authentication.api.router import router as authentication_router
from app.modules.doctor.api.router import router as doctor_router
from app.modules.organization.api.router import router as organization_router

api_router = APIRouter()
api_router.include_router(authentication_router, prefix="/auth", tags=["authentication"])
api_router.include_router(organization_router, prefix="/organizations", tags=["organization"])
api_router.include_router(doctor_router, prefix="/doctors", tags=["doctor"])
