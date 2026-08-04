"""`LabRecommendationService` — this task's own explicitly-named
APPLICATION service, covering "Suggested Follow-up Tests" and "Monitoring
Recommendations" list hygiene plus deterministic recommendation
derivation from critical findings.

`find_duplicate`/`deduplicate` mirror
`app.modules.medical_reasoning_ai.application.services
.recommendation_reasoning_service.RecommendationReasoningService`'s own
pure list-hygiene utilities exactly (this task's own VALIDATION list does
not name an "inconsistent recommendations" category the way that
module's task did, so these are used purely as non-throwing enrichment
here, never as a validation gate).

`derive_follow_up_for_critical_findings` is this service's own
recommendation-*derivation* contribution: for every finding reconciled to
a critical flag, deterministically suggesting a repeat test to rule out
lab error is universally standard clinical practice for any critical
result — not test-specific protocol knowledge that would need a fragile,
incomplete reference table — so it is safe to derive generically rather
than left entirely to the AI.
"""

from app.modules.lab_interpretation_ai.domain.enums import LabFindingFlag
from app.modules.lab_interpretation_ai.domain.value_objects import LabFinding

_CRITICAL_FLAGS = (LabFindingFlag.CRITICAL_LOW, LabFindingFlag.CRITICAL_HIGH)


class LabRecommendationService:
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
        self, findings: tuple[LabFinding, ...]
    ) -> tuple[str, ...]:
        return tuple(
            f"Repeat {finding.test_name} to confirm critical result"
            for finding in findings
            if finding.flag in _CRITICAL_FLAGS
        )
