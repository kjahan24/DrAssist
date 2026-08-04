"""HTTP routes for the AI Lab Interpretation module.

A placeholder health route only — no generation endpoint yet, matching
every prior AI module's own "placeholder endpoints only" precedent (no
`CurrentUser`/permission dependency, mirroring
`app.api.v1.endpoints.health`'s "a liveness-style probe has no bearer
token" reasoning).
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def get_lab_interpretation_ai_health() -> dict[str, str]:
    return {"status": "ok", "module": "lab_interpretation_ai"}
