"""`MedicationSafetyAnalysisService` — the deterministic half of this
task's own "MEDICATION SAFETY" requirement. See
`app.modules.prescription_ai.domain.value_objects.MedicationSafetyFinding`'s
own docstring for the full split between AI-reported and deterministic
findings, and why both exist.

Lives in `application/services/`, not `infrastructure/`, the same
placement `app.modules.icd10_ai.application.services
.icd10_ranking_service.ICD10RankingService` uses for itself: an
application-layer service depending on its own module's ports
(`DrugInteractionPort`, `MedicationKnowledgePort`), constructor-injected.

Three checks, each independently testable:

1. Drug-drug interactions — delegated entirely to
   `DrugInteractionPort.check_interactions` (a curated reference table;
   see that port's own docstring for why this cannot be a complete
   real-world interaction database).
2. Allergy cross-reactions — delegated to
   `DrugInteractionPort.check_allergy_conflicts`.
3. Duplicate therapeutic class — computed directly here via
   `MedicationKnowledgePort.lookup_therapeutic_class`: the first
   medication (by input order) claims a therapeutic class; any later
   medication sharing that same class produces a
   `SafetyFindingCategory.DUPLICATE_THERAPY` finding. Medications whose
   therapeutic class is not in the curated reference set
   (`lookup_therapeutic_class` returns `None`) are silently skipped for
   this check — absence from a necessarily-incomplete reference set is
   not evidence of anything, the same "soft signal" reasoning
   `MedicationKnowledgePort`'s own docstring documents.

`existing_medications` (the patient's current medication list, supplied
by the caller) is folded into the same name pool as the newly-suggested
medications for all three checks — a new prescription can interact with,
duplicate, or conflict against a drug the patient is already taking, not
only against another drug in the same suggestion set.
"""

from app.modules.prescription_ai.application.ports import (
    DrugInteractionPort,
    MedicationKnowledgePort,
)
from app.modules.prescription_ai.domain.enums import SafetyFindingCategory, SafetySeverity
from app.modules.prescription_ai.domain.value_objects import (
    MedicationSafetyFinding,
    MedicationSuggestion,
)


class MedicationSafetyAnalysisService:
    def __init__(
        self, *, drug_interaction: DrugInteractionPort, knowledge: MedicationKnowledgePort
    ) -> None:
        self._drug_interaction = drug_interaction
        self._knowledge = knowledge

    def analyze(
        self,
        *,
        medications: tuple[MedicationSuggestion, ...],
        existing_medications: tuple[str, ...] = (),
        allergies: tuple[str, ...] = (),
    ) -> tuple[MedicationSafetyFinding, ...]:
        all_names = tuple(m.generic_name for m in medications) + existing_medications

        findings: list[MedicationSafetyFinding] = []
        findings.extend(self._drug_interaction.check_interactions(all_names))
        findings.extend(self._drug_interaction.check_allergy_conflicts(all_names, allergies))
        findings.extend(self._check_duplicate_therapy(all_names))
        return tuple(findings)

    def _check_duplicate_therapy(
        self, generic_names: tuple[str, ...]
    ) -> tuple[MedicationSafetyFinding, ...]:
        seen_classes: dict[str, str] = {}
        findings: list[MedicationSafetyFinding] = []
        for name in generic_names:
            if not name.strip():
                continue
            therapeutic_class = self._knowledge.lookup_therapeutic_class(name)
            if therapeutic_class is None:
                continue
            existing = seen_classes.get(therapeutic_class)
            if existing is not None and existing.strip().lower() != name.strip().lower():
                findings.append(
                    MedicationSafetyFinding(
                        category=SafetyFindingCategory.DUPLICATE_THERAPY,
                        severity=SafetySeverity.MODERATE,
                        description=(
                            f"{existing!r} and {name!r} are both {therapeutic_class} — "
                            "potential duplicate therapy."
                        ),
                        affected_medications=(existing, name),
                    )
                )
            else:
                seen_classes.setdefault(therapeutic_class, name)
        return tuple(findings)
