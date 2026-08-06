"""Unit test for the Medical Topics module's health route. Calls the
route function directly — it has no dependencies (no DB session, no
auth), so there is nothing an end-to-end HTTP request adds over calling
it in-process."""

from app.modules.medical_topics.presentation.router import get_medical_topics_health


class TestMedicalTopicsHealthRoute:
    async def test_returns_ok_status(self) -> None:
        result = await get_medical_topics_health()
        assert result == {"status": "ok", "module": "medical_topics"}
