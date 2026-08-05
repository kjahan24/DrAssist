"""`StaticDoseAdjustmentKnowledgeBase` — the one concrete
`DoseAdjustmentPort` implementation this task ships: small, curated
lists of renally-/hepatically-cleared medications, combined with a
simple keyword/`eGFR`-pattern impairment detector applied to this task's
own free-text `renal_function`/`hepatic_function` SUPPORTED INPUT
fields. A real production system might instead consult structured lab
values and a licensed dosing-adjustment reference here; this module's
own small, rule-based implementation is the pragmatic in-repo
substitute, the same "each module defines its own local, necessarily-
incomplete copy" precedent every prior AI module's own knowledge-base
adapter establishes for itself.
"""

import re

from app.modules.drug_interaction_ai.application.ports import DoseAdjustmentPort
from app.modules.drug_interaction_ai.domain.value_objects import MedicationEntry

_RENALLY_CLEARED_DRUGS = frozenset({"metformin", "gabapentin", "digoxin"})
_HEPATICALLY_CLEARED_DRUGS = frozenset({"acetaminophen", "simvastatin", "phenytoin"})

_IMPAIRMENT_KEYWORDS = ("impair", "failure", "ckd", "reduced", "insufficiency", "disease")
_EGFR_PATTERN = re.compile(r"egfr\D{0,5}(\d+)")
_EGFR_IMPAIRMENT_THRESHOLD = 60


def _suggests_impairment(text: str | None) -> bool:
    if not text or not text.strip():
        return False
    text_lower = text.lower()
    if any(keyword in text_lower for keyword in _IMPAIRMENT_KEYWORDS):
        return True
    match = _EGFR_PATTERN.search(text_lower)
    return match is not None and int(match.group(1)) < _EGFR_IMPAIRMENT_THRESHOLD


class StaticDoseAdjustmentKnowledgeBase(DoseAdjustmentPort):
    def suggest_dose_adjustment(
        self,
        medication: MedicationEntry,
        *,
        renal_function: str | None,
        hepatic_function: str | None,
    ) -> str | None:
        drug_key = medication.drug_name.strip().lower()

        if drug_key in _RENALLY_CLEARED_DRUGS and _suggests_impairment(renal_function):
            return (
                f"Renal dose adjustment recommended for {medication.drug_name} given "
                f"reported renal function: {renal_function}."
            )

        if drug_key in _HEPATICALLY_CLEARED_DRUGS and _suggests_impairment(hepatic_function):
            return (
                f"Hepatic dose adjustment recommended for {medication.drug_name} given "
                f"reported liver function: {hepatic_function}."
            )

        return None
