"""HTTP routes for the AI Medical Reasoning Engine.

A placeholder health route only — no generation endpoint yet, matching
`app.modules.differential_diagnosis_ai.presentation.router`'s own
"placeholder endpoints only" precedent (no `CurrentUser`/permission
dependency, mirroring `app.api.v1.endpoints.health`'s "a liveness-style
probe has no bearer token" reasoning). This task's own GOAL section is
explicit that this module "is NOT an endpoint that clinicians use
directly" — it is a reasoning layer other backend modules call through
`public/interfaces.py::MedicalReasoningAIPort`, not a clinician-facing
API surface; this route exists only for the same operational-liveness
reason every other module's health route does, and no further HTTP
surface is added.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def get_medical_reasoning_ai_health() -> dict[str, str]:
    return {"status": "ok", "module": "medical_reasoning_ai"}
