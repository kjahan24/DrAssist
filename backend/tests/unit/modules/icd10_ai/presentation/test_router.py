"""Unit test for the AI ICD-10 Coding module's placeholder route. Calls
the route function directly — it has no dependencies (no DB session, no
auth), so there is nothing an end-to-end HTTP request adds over calling
it in-process."""

from app.modules.icd10_ai.presentation.router import get_icd10_ai_health


class TestICD10AIHealthRoute:
    async def test_returns_ok_status(self) -> None:
        result = await get_icd10_ai_health()
        assert result == {"status": "ok", "module": "icd10_ai"}
