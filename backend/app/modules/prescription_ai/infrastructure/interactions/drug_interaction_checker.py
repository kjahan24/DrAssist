"""`StaticDrugInteractionChecker` — the one concrete `DrugInteractionPort`
implementation this task ships. See that port's own docstring
(`application/ports.py`) for why this is a deterministic safety net
independent of the AI's own self-reported findings.

`_INTERACTION_PAIRS` and `_ALLERGY_CROSS_REACTIONS` are small curated
reference tables — a real production system would call a licensed,
regularly-updated drug-interaction database/API here instead; this
module's own small, self-contained implementation is the pragmatic
in-repo substitute, the same "each module defines its own local,
necessarily-incomplete copy" precedent
`app.modules.prescription_ai.infrastructure.knowledge
.medication_knowledge_base.StaticMedicationKnowledgeBase` establishes
for its own sibling table.
"""

import itertools

from app.modules.prescription_ai.application.ports import DrugInteractionPort
from app.modules.prescription_ai.domain.enums import SafetyFindingCategory, SafetySeverity
from app.modules.prescription_ai.domain.value_objects import MedicationSafetyFinding

_INTERACTION_PAIRS: dict[frozenset[str], tuple[SafetySeverity, str]] = {
    frozenset({"warfarin", "aspirin"}): (
        SafetySeverity.HIGH,
        "Combining warfarin with aspirin significantly increases bleeding risk.",
    ),
    frozenset({"warfarin", "ibuprofen"}): (
        SafetySeverity.HIGH,
        "NSAIDs increase bleeding risk when combined with warfarin.",
    ),
    frozenset({"warfarin", "naproxen"}): (
        SafetySeverity.HIGH,
        "NSAIDs increase bleeding risk when combined with warfarin.",
    ),
    frozenset({"warfarin", "azithromycin"}): (
        SafetySeverity.MODERATE,
        "Macrolide antibiotics may potentiate warfarin's anticoagulant effect.",
    ),
    frozenset({"lisinopril", "losartan"}): (
        SafetySeverity.MODERATE,
        "Combining an ACE inhibitor and an ARB increases risk of hyperkalemia and renal "
        "impairment without added benefit.",
    ),
    frozenset({"lisinopril", "spironolactone"}): (
        SafetySeverity.MODERATE,
        "ACE inhibitor plus a potassium-sparing diuretic increases hyperkalemia risk.",
    ),
    frozenset({"sertraline", "tramadol"}): (
        SafetySeverity.HIGH,
        "Increased risk of serotonin syndrome when an SSRI is combined with tramadol.",
    ),
    frozenset({"fluoxetine", "tramadol"}): (
        SafetySeverity.HIGH,
        "Increased risk of serotonin syndrome when an SSRI is combined with tramadol.",
    ),
    frozenset({"simvastatin", "clarithromycin"}): (
        SafetySeverity.HIGH,
        "Macrolide antibiotics raise simvastatin levels, increasing myopathy/rhabdomyolysis "
        "risk.",
    ),
    frozenset({"metformin", "furosemide"}): (
        SafetySeverity.LOW,
        "Loop diuretics may affect renal function relevant to metformin clearance.",
    ),
}

_ALLERGY_CROSS_REACTIONS: dict[str, tuple[str, ...]] = {
    "penicillin": ("amoxicillin", "amoxicillin-clavulanate", "ampicillin", "penicillin"),
    "sulfa": ("hydrochlorothiazide",),
    "nsaid": ("ibuprofen", "naproxen", "aspirin", "diclofenac"),
    "aspirin": ("aspirin",),
    "codeine": ("hydrocodone", "oxycodone", "tramadol", "morphine"),
}


class StaticDrugInteractionChecker(DrugInteractionPort):
    def check_interactions(
        self, generic_names: tuple[str, ...]
    ) -> tuple[MedicationSafetyFinding, ...]:
        normalized = [name.strip().lower() for name in generic_names if name.strip()]
        findings: list[MedicationSafetyFinding] = []
        seen_pairs: set[frozenset[str]] = set()
        for name_a, name_b in itertools.combinations(normalized, 2):
            pair = frozenset({name_a, name_b})
            if len(pair) < 2 or pair in seen_pairs:
                continue
            entry = _INTERACTION_PAIRS.get(pair)
            if entry is None:
                continue
            severity, description = entry
            findings.append(
                MedicationSafetyFinding(
                    category=SafetyFindingCategory.DRUG_INTERACTION,
                    severity=severity,
                    description=description,
                    affected_medications=tuple(sorted(pair)),
                )
            )
            seen_pairs.add(pair)
        return tuple(findings)

    def check_allergy_conflicts(
        self, generic_names: tuple[str, ...], allergies: tuple[str, ...]
    ) -> tuple[MedicationSafetyFinding, ...]:
        normalized_meds = [name.strip().lower() for name in generic_names if name.strip()]
        normalized_allergies = [a.strip().lower() for a in allergies if a.strip()]
        findings: list[MedicationSafetyFinding] = []
        seen: set[tuple[str, str]] = set()
        for allergy in normalized_allergies:
            trigger_medications = _ALLERGY_CROSS_REACTIONS.get(allergy, ())
            for medication in normalized_meds:
                if medication in trigger_medications and (allergy, medication) not in seen:
                    findings.append(
                        MedicationSafetyFinding(
                            category=SafetyFindingCategory.ALLERGY_CONFLICT,
                            severity=SafetySeverity.HIGH,
                            description=(
                                f"Patient has a documented {allergy} allergy; {medication} is "
                                "cross-reactive."
                            ),
                            affected_medications=(medication,),
                        )
                    )
                    seen.add((allergy, medication))
        return tuple(findings)
