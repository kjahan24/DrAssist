"""HTTP routes for the AI Clinical Note Generation module.

A placeholder health route only — no generation endpoint yet, matching
`app.modules.ai_copilot.api.router`'s own "placeholder endpoints only"
precedent (no `CurrentUser`/permission dependency, mirroring
`app.api.v1.endpoints.health`'s "a liveness-style probe has no bearer
token" reasoning). A future consumer module wires a real, authenticated
generation endpoint against `public/interfaces.py::ClinicalNoteAIPort`.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def get_clinical_note_ai_health() -> dict[str, str]:
    return {"status": "ok", "module": "clinical_note_ai"}
