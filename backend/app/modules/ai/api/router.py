"""HTTP routes for the AI module.

Empty for this task — see `container.py`'s scope note: this task builds
the reusable AI Foundation only, no clinical feature with its own
endpoints yet. Wired into `app.api.v1.router` now (empty) so it is present
in the app/OpenAPI schema from day one and so a future AI-feature module
only needs to register routes into this file, following the exact pattern
`app.api.v1.router`'s own docstring already establishes for
`family_access`/`notification` before their first endpoint existed.
"""

from fastapi import APIRouter

router = APIRouter()
