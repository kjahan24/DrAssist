"""Unit test for the AI Differential Diagnosis module's placeholder
route. Calls the route function directly — it has no dependencies (no DB
session, no auth), so there is nothing an end-to-end HTTP request adds
over calling it in-process."""

from app.modules.differential_diagnosis_ai.presentation.router import (
    get_differential_diagnosis_ai_health,
)


class TestDifferentialDiagnosisAIHealthRoute:
    async def test_returns_ok_status(self) -> None:
        result = await get_differential_diagnosis_ai_health()
        assert result == {"status": "ok", "module": "differential_diagnosis_ai"}
