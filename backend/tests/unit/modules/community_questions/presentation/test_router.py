"""Unit test for the Community Questions module's health route. Calls
the route function directly — it has no dependencies (no DB session, no
auth), so there is nothing an end-to-end HTTP request adds over calling
it in-process."""

from app.modules.community_questions.presentation.router import get_community_questions_health


class TestCommunityQuestionsHealthRoute:
    async def test_returns_ok_status(self) -> None:
        result = await get_community_questions_health()
        assert result == {"status": "ok", "module": "community_questions"}
