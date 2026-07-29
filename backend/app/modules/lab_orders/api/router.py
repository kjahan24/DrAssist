"""HTTP routes for the Lab Orders module.

No endpoints registered yet — this phase builds the module's foundation
only (see `app.modules.lab_orders.container`). Registered into
`app.api.v1.router` now so it is present in the app/OpenAPI schema from
day one, matching `app.modules.prescriptions.api.router`.
"""

from fastapi import APIRouter

router = APIRouter()
