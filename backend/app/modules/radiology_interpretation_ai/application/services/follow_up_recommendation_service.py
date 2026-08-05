"""`FollowUpRecommendationService` — this task's own explicitly-named
APPLICATION service, covering "Differential Imaging Considerations",
"Suggested Follow-up Imaging", and "Suggested Specialist Referral" list
hygiene, and the source of truth for this task's own "inconsistent
recommendations" VALIDATION category.

`find_duplicate`/`deduplicate` mirror every prior AI module's own
recommendation-hygiene service exactly. Unlike
`app.modules.lab_interpretation_ai.application.services
.lab_recommendation_service.LabRecommendationService` (whose task did
not name "inconsistent recommendations" as a VALIDATION category),
*this* task's own VALIDATION list explicitly does — so
`find_duplicate` additionally backs a real validation gate
(`infrastructure/validation/radiology_interpretation_validator.py`),
not merely enrichment-time cleanup, the same "Do NOT duplicate
implementations" rule `app.modules.medical_reasoning_ai.application
.services.recommendation_reasoning_service.RecommendationReasoningService`
documents for itself.

`derive_follow_up_for_critical_findings`/
`derive_specialist_referral_for_critical_findings` are this service's own
recommendation-*derivation* contribution: for every finding reconciled to
`RadiologyFindingCategory.CRITICAL`, deterministically suggesting
"further imaging correlation" and "urgent specialist referral" is safe,
generic clinical practice for any critical imaging finding — not
modality- or organ-specific protocol knowledge that would need a
fragile, incomplete reference table.
"""

from app.modules.radiology_interpretation_ai.domain.enums import RadiologyFindingCategory
from app.modules.radiology_interpretation_ai.domain.value_objects import RadiologyFinding

_CRITICAL = RadiologyFindingCategory.CRITICAL


class FollowUpRecommendationService:
    def find_duplicate(self, items: tuple[str, ...]) -> str | None:
        seen: set[str] = set()
        for item in items:
            normalized = item.strip().lower()
            if not normalized:
                continue
            if normalized in seen:
                return item
            seen.add(normalized)
        return None

    def deduplicate(self, items: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        deduplicated: list[str] = []
        for item in items:
            normalized = item.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                deduplicated.append(item)
        return tuple(deduplicated)

    def derive_follow_up_for_critical_findings(
        self, findings: tuple[RadiologyFinding, ...]
    ) -> tuple[str, ...]:
        return tuple(
            f"Further imaging correlation recommended for: {finding.description}"
            for finding in findings
            if finding.category is _CRITICAL
        )

    def derive_specialist_referral_for_critical_findings(
        self, findings: tuple[RadiologyFinding, ...]
    ) -> tuple[str, ...]:
        return tuple(
            f"Urgent specialist referral recommended given critical finding: "
            f"{finding.description}"
            for finding in findings
            if finding.category is _CRITICAL
        )
