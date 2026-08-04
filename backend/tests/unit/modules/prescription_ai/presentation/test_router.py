"""Unit test for the AI Prescription Assistance module's placeholder
route. Calls the route function directly — it has no dependencies (no DB
session, no auth), so there is nothing an end-to-end HTTP request adds
over calling it in-process."""

from app.modules.prescription_ai.presentation.router import get_prescription_ai_health


class TestPrescriptionAIHealthRoute:
    async def test_returns_ok_status(self) -> None:
        result = await get_prescription_ai_health()
        assert result == {"status": "ok", "module": "prescription_ai"}
