"""HTTP-level (router) API tests.

Every test here drives requests through a real `uvicorn` server running
`app.main.app` (see `conftest.py`'s `live_server` fixture for why not
`ASGITransport`), which means every request eventually uses
`app.infrastructure.database.session.engine` — a process-lifetime
singleton whose asyncpg connection pool binds to whatever event loop is
running the first time it's used. Since pytest-asyncio otherwise gives
each test function its own fresh event loop, a *second* test touching
that singleton engine under a *different* loop breaks it (`RuntimeError:
Task ... attached to a different loop`, or an asyncpg-level error on the
`pool_pre_ping` check) — every test module in this package opts into one
shared, session-scoped loop instead, so the singleton engine sees a
consistent loop for the whole run. `conftest.py`'s async fixtures are
marked with the matching `loop_scope="session"` for the same reason.

The opt-in is `pytestmark = pytest.mark.asyncio(loop_scope="session")`,
declared directly in *every individual test module* in this package
(see e.g. `test_health_api.py`) — not here. Two mechanisms that look
like they should let this be declared once, package-wide, were tried and
confirmed *not* to work by directly comparing
`id(asyncio.get_running_loop())` between `live_server` and a real test
function: a bare `pytestmark` assignment in this `__init__.py` (pytest
only reads `pytestmark` as an attribute of the test module actually
being collected, never a package's `__init__.py`), and adding the marker
to every collected item from a `pytest_collection_modifyitems` hook in
`conftest.py` (pytest-asyncio decides and caches each test's loop scope
during its own, earlier collection hook, before
`pytest_collection_modifyitems` ever runs — the added marker arrives too
late to change anything, even though it visibly attaches to the item).
Without the mark, a test runs on pytest-asyncio's normal per-function
loop while `live_server` runs on the session loop, and closing
`live_server`'s connection from the test's own already-closed loop
raises `RuntimeError: Event loop is closed`.
"""
