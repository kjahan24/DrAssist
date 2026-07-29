"""HTTP routes for the Clinical Notes module.

No endpoints registered yet — this phase builds the module's foundation
only (see `app.modules.clinical_notes.container`). Registered into
`app.api.v1.router` now so it is present in the app/OpenAPI schema from
day one, matching `app.modules.attachments.api.router`.
"""

from fastapi import APIRouter

router = APIRouter()
