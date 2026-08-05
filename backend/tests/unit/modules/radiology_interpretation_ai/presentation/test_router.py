"""Unit test for the AI Radiology Interpretation module's placeholder
route. Calls the route function directly — it has no dependencies (no DB
session, no auth), so there is nothing an end-to-end HTTP request adds
over calling it in-process."""

from app.modules.radiology_interpretation_ai.presentation.router import (
    get_radiology_interpretation_ai_health,
)


class TestRadiologyInterpretationAIHealthRoute:
    async def test_returns_ok_status(self) -> None:
        result = await get_radiology_interpretation_ai_health()
        assert result == {"status": "ok", "module": "radiology_interpretation_ai"}
