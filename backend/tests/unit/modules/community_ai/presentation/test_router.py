"""Unit test for the Community AI Features module's health route. Calls
the route function directly — it has no dependencies (no DB session, no
auth), so there is nothing an end-to-end HTTP request adds over calling
it in-process."""

from app.modules.community_ai.presentation.router import get_community_ai_health


class TestCommunityAIHealthRoute:
    async def test_returns_ok_status(self) -> None:
        result = await get_community_ai_health()
        assert result == {"status": "ok", "module": "community_ai"}
