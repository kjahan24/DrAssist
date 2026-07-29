"""HTTP routes for the Procedures module.

No endpoints registered yet — this phase builds the module's foundation
only (see `app.modules.procedures.container`). Registered into
`app.api.v1.router` now so it is present in the app/OpenAPI schema from
day one, matching `app.modules.diagnosis.api.router`.
"""

from fastapi import APIRouter

router = APIRouter()
