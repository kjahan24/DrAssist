"""Unit test for the AI Drug Interaction & Medication Safety module's
placeholder route. Calls the route function directly — it has no
dependencies (no DB session, no auth), so there is nothing an end-to-end
HTTP request adds over calling it in-process."""

from app.modules.drug_interaction_ai.presentation.router import get_drug_interaction_ai_health


class TestDrugInteractionAIHealthRoute:
    async def test_returns_ok_status(self) -> None:
        result = await get_drug_interaction_ai_health()
        assert result == {"status": "ok", "module": "drug_interaction_ai"}
