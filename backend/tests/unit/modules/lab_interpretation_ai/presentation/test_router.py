"""Unit test for the AI Lab Interpretation module's placeholder route.
Calls the route function directly — it has no dependencies (no DB
session, no auth), so there is nothing an end-to-end HTTP request adds
over calling it in-process."""

from app.modules.lab_interpretation_ai.presentation.router import (
    get_lab_interpretation_ai_health,
)


class TestLabInterpretationAIHealthRoute:
    async def test_returns_ok_status(self) -> None:
        result = await get_lab_interpretation_ai_health()
        assert result == {"status": "ok", "module": "lab_interpretation_ai"}
