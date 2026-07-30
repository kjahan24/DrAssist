"""HTTP routes for the Patient History module.

No endpoints registered — this task explicitly excludes API endpoints
(see `app.modules.patient_history.container`). Registered into
`app.api.v1.router` now so it is present in the app/OpenAPI schema from
day one, matching `app.modules.doctor_review.api.router`.
"""

from fastapi import APIRouter

router = APIRouter()
