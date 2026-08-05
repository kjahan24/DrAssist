"""`ClinicalCorrelationService` — this task's own explicitly-named
APPLICATION service, covering "Correlation Recommendations", "Suggested
Follow-up", and "Suggested Specialist Referral" list hygiene, and the
source of truth for this task's own "inconsistent conclusions"
VALIDATION category.

`find_duplicate`/`deduplicate` mirror every prior AI module's own
recommendation-hygiene service exactly. This task's own VALIDATION list
explicitly names "inconsistent conclusions", so `find_duplicate`
additionally backs a real validation gate (`infrastructure/validation
/pathology_interpretation_validator.py`), not merely enrichment-time
cleanup, the same "Do NOT duplicate implementations" rule every prior AI
module's own recommendation service documents for itself.

`derive_correlation_recommendations_for_malignant_findings`/
`derive_follow_up_for_malignant_findings`/
`derive_specialist_referral_for_malignant_findings` are this service's
own recommendation-*derivation* contribution: for every finding
reconciled to `PathologyFindingCategory.MALIGNANT`, deterministically
suggesting ancillary-study correlation, confirmatory follow-up, and an
urgent oncology/specialist referral is safe, generic clinical practice
for any malignant pathology finding — not specimen- or organ-specific
protocol knowledge that would need a fragile, incomplete reference
table.
"""

from app.modules.pathology_interpretation_ai.domain.enums import PathologyFindingCategory
from app.modules.pathology_interpretation_ai.domain.value_objects import PathologyFinding

_MALIGNANT = PathologyFindingCategory.MALIGNANT


class ClinicalCorrelationService:
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

    def derive_correlation_recommendations_for_malignant_findings(
        self, findings: tuple[PathologyFinding, ...]
    ) -> tuple[str, ...]:
        return tuple(
            f"Ancillary study correlation (IHC/molecular) recommended for: {finding.description}"
            for finding in findings
            if finding.category is _MALIGNANT
        )

    def derive_follow_up_for_malignant_findings(
        self, findings: tuple[PathologyFinding, ...]
    ) -> tuple[str, ...]:
        return tuple(
            f"Confirmatory follow-up recommended for malignant finding: {finding.description}"
            for finding in findings
            if finding.category is _MALIGNANT
        )

    def derive_specialist_referral_for_malignant_findings(
        self, findings: tuple[PathologyFinding, ...]
    ) -> tuple[str, ...]:
        return tuple(
            f"Urgent oncology referral recommended given malignant finding: {finding.description}"
            for finding in findings
            if finding.category is _MALIGNANT
        )
