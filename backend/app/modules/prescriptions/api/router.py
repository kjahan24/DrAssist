"""HTTP routes for the Prescription module.

No endpoints registered yet — this phase builds the module's foundation
only (see `app.modules.prescriptions.container`). Registered into
`app.api.v1.router` now so it is present in the app/OpenAPI schema from
day one, matching `app.modules.soap_notes.api.router`.
"""

from fastapi import APIRouter

router = APIRouter()
