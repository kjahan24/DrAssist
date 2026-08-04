"""Unit test for the AI SOAP Note Generation module's placeholder route.
Calls the route function directly — it has no dependencies (no DB
session, no auth), so there is nothing an end-to-end HTTP request adds
over calling it in-process."""

from app.modules.soap_note_ai.presentation.router import get_soap_note_ai_health


class TestSOAPNoteAIHealthRoute:
    async def test_returns_ok_status(self) -> None:
        result = await get_soap_note_ai_health()
        assert result == {"status": "ok", "module": "soap_note_ai"}
