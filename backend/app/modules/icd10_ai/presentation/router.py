"""HTTP routes for the AI ICD-10 Coding module.

A placeholder health route only — no generation endpoint yet, matching
`app.modules.soap_note_ai.presentation.router`'s own "placeholder
endpoints only" precedent (no `CurrentUser`/permission dependency,
mirroring `app.api.v1.endpoints.health`'s "a liveness-style probe has no
bearer token" reasoning). A future consumer module wires a real,
authenticated generation endpoint against `public/interfaces.py
::ICD10AIPort`.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def get_icd10_ai_health() -> dict[str, str]:
    return {"status": "ok", "module": "icd10_ai"}
