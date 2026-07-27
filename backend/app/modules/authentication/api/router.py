"""Authentication module route aggregator.

No endpoints are registered yet — login, register, refresh, and logout
are explicitly out of scope for this task (see `container.py`). Included
into `app/api/v1/router.py` now so the module is present in the OpenAPI
schema/app wiring from day one; endpoint modules will be added under this
package and `include_router`'d here, e.g.:

    from app.modules.authentication.api.endpoints import login
    router.include_router(login.router, tags=["authentication"])
"""

from fastapi import APIRouter

router = APIRouter()
