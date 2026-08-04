"""Unit test for the AI Medical Reasoning Engine's placeholder route.
Calls the route function directly — it has no dependencies (no DB
session, no auth), so there is nothing an end-to-end HTTP request adds
over calling it in-process."""

from app.modules.medical_reasoning_ai.presentation.router import get_medical_reasoning_ai_health


class TestMedicalReasoningAIHealthRoute:
    async def test_returns_ok_status(self) -> None:
        result = await get_medical_reasoning_ai_health()
        assert result == {"status": "ok", "module": "medical_reasoning_ai"}
