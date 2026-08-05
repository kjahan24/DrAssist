"""`AlternativeMedicationService` — this task's own explicitly-named
APPLICATION service, covering "Alternative Medication Suggestions" list
hygiene and its own deterministic derivation, plus the general list/
issue-collection hygiene every list-shaped OUTPUT field needs.

`find_duplicate`/`deduplicate` mirror every prior AI module's own
recommendation-hygiene service exactly. `deduplicate_issues` is this
module's own extension of that same idea to `SafetyIssue` objects
(needed because this task's OUTPUT specification structures
"Interaction List" as objects, not plain strings, unlike every prior AI
module's own recommendation lists) — items are deduplicated by
normalized `description`, keeping the first occurrence, the same
case-insensitive, whitespace-insensitive comparison `deduplicate` uses
for plain strings.

`derive_alternatives_for_high_severity_issues` is this service's own
recommendation-*derivation* contribution: for every issue reconciled to
`SafetySeverity.MAJOR` or `CONTRAINDICATED`, deterministically suggesting
that an alternative medication be considered is safe, generic clinical
practice for any severe medication-safety concern — not drug-specific
substitution knowledge (which drug to switch *to*) that would need a
fragile, incomplete reference table.
"""

from app.modules.drug_interaction_ai.domain.enums import SafetySeverity
from app.modules.drug_interaction_ai.domain.value_objects import SafetyIssue

_HIGH_SEVERITY = (SafetySeverity.MAJOR, SafetySeverity.CONTRAINDICATED)


class AlternativeMedicationService:
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

    def deduplicate_issues(self, issues: tuple[SafetyIssue, ...]) -> tuple[SafetyIssue, ...]:
        seen: set[str] = set()
        deduplicated: list[SafetyIssue] = []
        for issue in issues:
            normalized = issue.description.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                deduplicated.append(issue)
        return tuple(deduplicated)

    def derive_alternatives_for_high_severity_issues(
        self, issues: tuple[SafetyIssue, ...]
    ) -> tuple[str, ...]:
        suggestions: list[str] = []
        for issue in issues:
            if issue.severity not in _HIGH_SEVERITY:
                continue
            medications = ", ".join(issue.involved_medications) or issue.description
            suggestions.append(
                f"Consider an alternative to {medications} given {issue.severity.value} risk: "
                f"{issue.description}"
            )
        return tuple(suggestions)
