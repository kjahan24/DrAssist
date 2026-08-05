"""Unit tests for `DoseAdjustmentService`."""

from app.modules.drug_interaction_ai.application.services.dose_adjustment_service import (
    DoseAdjustmentService,
)
from tests.unit.modules.drug_interaction_ai.application.fakes import (
    FakeDoseAdjustmentPort,
    make_medication,
)


class TestSuggestDoseAdjustments:
    def test_returns_empty_when_the_port_has_no_data(self) -> None:
        service = DoseAdjustmentService(port=FakeDoseAdjustmentPort())
        result = service.suggest_dose_adjustments(
            (make_medication(),), renal_function=None, hepatic_function=None
        )
        assert result == ()

    def test_collects_suggestions_from_every_medication(self) -> None:
        port = FakeDoseAdjustmentPort(suggestion="Reduce dose given renal impairment.")
        service = DoseAdjustmentService(port=port)

        result = service.suggest_dose_adjustments(
            (make_medication(drug_name="A"), make_medication(drug_name="B")),
            renal_function="eGFR 25",
            hepatic_function=None,
        )

        assert result == (
            "Reduce dose given renal impairment.",
            "Reduce dose given renal impairment.",
        )

    def test_passes_renal_and_hepatic_function_through_to_the_port(self) -> None:
        port = FakeDoseAdjustmentPort()
        service = DoseAdjustmentService(port=port)

        service.suggest_dose_adjustments(
            (make_medication(),), renal_function="eGFR 25", hepatic_function="Child-Pugh B"
        )

        assert len(port.calls) == 1
