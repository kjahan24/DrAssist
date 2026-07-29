"""HTTP routes for the Clinical Reasoning module.

No endpoints registered yet — this phase builds the module's foundation
only (see `app.modules.clinical_reasoning.container`). Registered into
`app.api.v1.router` now so it is present in the app/OpenAPI schema from
day one, matching `app.modules.lab_results.api.router`.
"""

from fastapi import APIRouter

router = APIRouter()
