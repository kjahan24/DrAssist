"""HTTP routes for the Attachments module.

No endpoints registered yet — this phase builds the module's foundation
only (see `app.modules.attachments.container`). Registered into
`app.api.v1.router` now so it is present in the app/OpenAPI schema from
day one, matching `app.modules.procedures.api.router`.
"""

from fastapi import APIRouter

router = APIRouter()
