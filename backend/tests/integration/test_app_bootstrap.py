"""Smoke test verifying the ASGI app assembles correctly.

This guards the architecture wiring itself (settings -> logging ->
middlewares -> router), independent of any business logic.
"""

from fastapi import FastAPI


def test_create_app_returns_fastapi_instance() -> None:
    from app.main import create_app

    app = create_app()

    assert isinstance(app, FastAPI)
    assert app.title == "DrAssist"
