"""Unit test for the AI Clinical Note Generation module's placeholder
route. Calls the route function directly — it has no dependencies (no DB
session, no auth), so there is nothing an end-to-end HTTP request adds
over calling it in-process."""

from app.modules.clinical_note_ai.presentation.router import get_clinical_note_ai_health


class TestClinicalNoteAIHealthRoute:
    async def test_returns_ok_status(self) -> None:
        result = await get_clinical_note_ai_health()
        assert result == {"status": "ok", "module": "clinical_note_ai"}
