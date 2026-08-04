"""HTTP routes for the AI Differential Diagnosis module.

A placeholder health route only — no generation endpoint yet, matching
`app.modules.prescription_ai.presentation.router`'s own "placeholder
endpoints only" precedent (no `CurrentUser`/permission dependency,
mirroring `app.api.v1.endpoints.health`'s "a liveness-style probe has no
bearer token" reasoning). A future consumer module wires a real,
authenticated generation endpoint against `public/interfaces.py
::DifferentialDiagnosisAIPort`.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def get_differential_diagnosis_ai_health() -> dict[str, str]:
    return {"status": "ok", "module": "differential_diagnosis_ai"}
