"""Organization module route aggregator.

No endpoints are registered yet — this task builds the module's
foundation only (see `container.py`). Included into `app/api/v1/router.py`
now so the module is present in the OpenAPI schema/app wiring from day
one; endpoint modules will be added under this package and
`include_router`'d here, matching the Authentication module's pattern.
"""

from fastapi import APIRouter

router = APIRouter()
