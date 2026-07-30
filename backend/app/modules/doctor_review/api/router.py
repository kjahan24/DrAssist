"""HTTP routes for the Doctor Review module.

No endpoints registered — this task explicitly excludes API endpoints
(see `app.modules.doctor_review.container`). Registered into
`app.api.v1.router` now so it is present in the app/OpenAPI schema from
day one, matching `app.modules.icd10_coding.api.router`.
"""

from fastapi import APIRouter

router = APIRouter()
