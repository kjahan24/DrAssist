"""v1 API route aggregator.

No endpoints are registered yet. As feature modules are added under
`app/api/v1/endpoints/`, include them here, e.g.:

    from app.api.v1.endpoints import patients
    api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
"""

from fastapi import APIRouter

api_router = APIRouter()
