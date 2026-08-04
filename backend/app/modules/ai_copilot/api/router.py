"""HTTP routes for the AI Clinical Copilot module.

A placeholder health route only, per this task's "Create placeholder
endpoints only. No medical intelligence yet." No `CurrentUser`/permission
dependency, matching `app.api.v1.endpoints.health`'s own "a liveness-style
probe has no bearer token" reasoning — this route reports only that the
module is wired into the app, not the health of anything it depends on.
A future clinical-feature module adds its own authenticated routes here
(or in its own `api/router.py`, calling this module's `public/` facade),
following the pattern `app.modules.notification.api.router`'s own
docstring documents for "this module had no `api/` package before...".
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def get_ai_copilot_health() -> dict[str, str]:
    return {"status": "ok", "module": "ai_copilot"}
