"""Unit test for the AI Risk Stratification & Early Warning Score
module's placeholder route. Calls the route function directly — it has
no dependencies (no DB session, no auth), so there is nothing an
end-to-end HTTP request adds over calling it in-process."""

from app.modules.risk_stratification_ai.presentation.router import (
    get_risk_stratification_ai_health,
)


class TestRiskStratificationAIHealthRoute:
    async def test_returns_ok_status(self) -> None:
        result = await get_risk_stratification_ai_health()
        assert result == {"status": "ok", "module": "risk_stratification_ai"}
