"""Unit test for the AI Patient Education & Discharge Instructions
module's placeholder route. Calls the route function directly — it has
no dependencies (no DB session, no auth), so there is nothing an
end-to-end HTTP request adds over calling it in-process."""

from app.modules.patient_education_ai.presentation.router import (
    get_patient_education_ai_health,
)


class TestPatientEducationAIHealthRoute:
    async def test_returns_ok_status(self) -> None:
        result = await get_patient_education_ai_health()
        assert result == {"status": "ok", "module": "patient_education_ai"}
