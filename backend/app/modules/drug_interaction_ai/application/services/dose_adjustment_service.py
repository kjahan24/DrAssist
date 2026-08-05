"""`DoseAdjustmentService` — this task's own explicitly-named
APPLICATION service, covering the final two of this task's own eighteen
DETECT categories: renal dose adjustment and hepatic dose adjustment.

Delegates per-medication to `DoseAdjustmentPort.suggest_dose_adjustment`,
passing this task's own free-text `renal_function`/`hepatic_function`
SUPPORTED INPUT fields through unchanged — see that port's own docstring
for why they stay free text rather than a structured lab value.
"""

from app.modules.drug_interaction_ai.application.ports import DoseAdjustmentPort
from app.modules.drug_interaction_ai.domain.value_objects import MedicationEntry


class DoseAdjustmentService:
    def __init__(self, *, port: DoseAdjustmentPort) -> None:
        self._port = port

    def suggest_dose_adjustments(
        self,
        medications: tuple[MedicationEntry, ...],
        *,
        renal_function: str | None,
        hepatic_function: str | None,
    ) -> tuple[str, ...]:
        suggestions: list[str] = []
        for medication in medications:
            suggestion = self._port.suggest_dose_adjustment(
                medication, renal_function=renal_function, hepatic_function=hepatic_function
            )
            if suggestion is not None:
                suggestions.append(suggestion)
        return tuple(suggestions)
