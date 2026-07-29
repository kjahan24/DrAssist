"""HTTP routes for the ICD-10 Coding module.

No endpoints registered yet — this phase builds the module's foundation
only (see `app.modules.icd10_coding.container`). Registered into
`app.api.v1.router` now so it is present in the app/OpenAPI schema from
day one, matching `app.modules.differential_diagnosis.api.router`.
"""

from fastapi import APIRouter

router = APIRouter()
