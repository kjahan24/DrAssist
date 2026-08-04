"""`RecommendationReasoningService` — the "recommendation justification"
half of this task's own "REASONING ENGINE" section, and the source of
truth for this task's own "inconsistent recommendations" VALIDATION
category.

"Recommendation justification" is fundamentally the AI's own semantic
reasoning task, expressed directly through `MedicalReasoningResult
.clinical_justification` — this service's own contribution is ensuring
the three recommendation lists this task's OUTPUT specification names
("Suggested Next Questions", "Suggested Investigations", "Suggested
Monitoring") are each internally consistent: `find_duplicate` detects the
same recommendation repeated within a single list (a literal self-
contradiction — recommending the same thing twice is never a
deliberate, justified choice), which
`infrastructure/validation/medical_reasoning_validator.py` calls
directly (once per list) to raise `InconsistentRecommendationsError`,
per this task's own "Do NOT duplicate implementations" rule.

`deduplicate` is a pure utility in the same spirit — not wired into the
main generation pipeline (a duplicate recommendation is a hard validation
failure there, so enrichment-time deduplication would never run), but
exposed for a future caller (per this module's own "centralize clinical
reasoning so no AI module duplicates reasoning logic" charter) that
already has an assembled, unvalidated recommendation list and wants it
cleaned up directly.
"""


class RecommendationReasoningService:
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
