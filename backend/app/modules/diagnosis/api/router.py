"""HTTP routes for the Diagnosis module.

No endpoints registered yet — this phase builds the module's foundation
only (see `app.modules.diagnosis.container`). Registered into
`app.api.v1.router` now so it is present in the app/OpenAPI schema from
day one, matching `app.modules.chief_complaints.api.router`.
"""

from fastapi import APIRouter

router = APIRouter()
