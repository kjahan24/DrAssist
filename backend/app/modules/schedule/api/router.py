"""HTTP routes for the Schedule/Availability module.

No endpoints registered — this task explicitly excludes API endpoints
(see `app.modules.schedule.container`). Registered into
`app.api.v1.router` now so it is present in the app/OpenAPI schema from
day one, matching `app.modules.appointment.api.router`.
"""

from fastapi import APIRouter

router = APIRouter()
