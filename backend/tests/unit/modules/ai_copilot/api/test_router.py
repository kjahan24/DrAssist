"""Unit test for the AI Clinical Copilot module's placeholder route.

Calls the route function directly rather than through a full HTTP client
— it has no dependencies (no DB session, no auth), so there is nothing an
end-to-end request adds over calling it in-process.
"""

from app.modules.ai_copilot.api.router import get_ai_copilot_health


class TestAiCopilotHealthRoute:
    async def test_returns_ok_status(self) -> None:
        result = await get_ai_copilot_health()
        assert result == {"status": "ok", "module": "ai_copilot"}
