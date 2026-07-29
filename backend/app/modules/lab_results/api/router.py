"""HTTP routes for the Lab Results module.

No endpoints registered yet — this phase builds the module's foundation
only (see `app.modules.lab_results.container`). Registered into
`app.api.v1.router` now so it is present in the app/OpenAPI schema from
day one, matching `app.modules.lab_orders.api.router`.
"""

from fastapi import APIRouter

router = APIRouter()
