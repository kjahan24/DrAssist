"""Unit test for the AI Healthcare Orchestrator module's placeholder
route. Calls the route function directly — it has no dependencies (no
DB session, no auth), so there is nothing an end-to-end HTTP request
adds over calling it in-process."""

from app.modules.ai_orchestrator.presentation.router import get_ai_orchestrator_health


class TestAIOrchestratorHealthRoute:
    async def test_returns_ok_status(self) -> None:
        result = await get_ai_orchestrator_health()
        assert result == {"status": "ok", "module": "ai_orchestrator"}
