"""HTTP routes for the AI Drug Interaction & Medication Safety module.

A placeholder health route only — no generation endpoint yet, matching
every prior AI module's own "placeholder endpoints only" precedent (no
`CurrentUser`/permission dependency, mirroring
`app.api.v1.endpoints.health`'s "a liveness-style probe has no bearer
token" reasoning), and this task's own explicit "Create placeholder
endpoints only. No persistence. No database writes." API section.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def get_drug_interaction_ai_health() -> dict[str, str]:
    return {"status": "ok", "module": "drug_interaction_ai"}
