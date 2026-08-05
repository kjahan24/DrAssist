"""`CriticalFindingDetectionService` — this task's own explicitly-named
APPLICATION service, and the safety-net half of the
`FindingExtractionPort` seam (see that port's own docstring).

The AI's own `RadiologyFinding.category` classification is trusted by
default, but this service applies two independent, deterministic
cross-checks against it, the same "AI-reported plus a deterministic
floor/override, merged" enrichment shape
`app.modules.lab_interpretation_ai.application.services
.critical_value_detection_service.CriticalValueDetectionService`
establishes for its own module, applied here for patient-safety reasons
specific to radiology interpretation:

- `escalate_on_critical_keywords` — re-classifies each AI-reported
  finding's own description via `FindingExtractionPort
  .classify_description`; when the port recognizes critical language the
  AI itself did not flag as such, the finding's category is escalated.
  This catches a *severity misclassification* (the AI found it, but
  under-called its severity).
- `derive_findings_missed_by_ai` — given the deterministic candidate pool
  `application/services/finding_extraction_service.FindingExtractionService
  .extract` already produced for this same report (passed in, not
  re-derived here — the use case computes that pool exactly once), appends
  any critical-category candidate whose keyword phrase does not already
  appear (case-insensitively) inside any AI-reported finding's
  description. This catches an *omission* (the AI never mentioned it at
  all) — a deliberately simple, deterministic case-insensitive substring
  containment check rather than fuzzy NLP matching, since a real
  critical-keyword phrase either appears in the AI's own wording or it
  does not.
"""

from dataclasses import replace

from app.modules.radiology_interpretation_ai.application.ports import FindingExtractionPort
from app.modules.radiology_interpretation_ai.domain.enums import RadiologyFindingCategory
from app.modules.radiology_interpretation_ai.domain.value_objects import RadiologyFinding

_CRITICAL = RadiologyFindingCategory.CRITICAL


class CriticalFindingDetectionService:
    def __init__(self, *, extractor: FindingExtractionPort) -> None:
        self._extractor = extractor

    def has_critical_findings(self, findings: tuple[RadiologyFinding, ...]) -> bool:
        return any(finding.category is _CRITICAL for finding in findings)

    def escalate_on_critical_keywords(
        self, findings: tuple[RadiologyFinding, ...]
    ) -> tuple[RadiologyFinding, ...]:
        return tuple(self._maybe_escalate(finding) for finding in findings)

    def _maybe_escalate(self, finding: RadiologyFinding) -> RadiologyFinding:
        if finding.category is _CRITICAL:
            return finding
        deterministic_category = self._extractor.classify_description(finding.description)
        if deterministic_category is _CRITICAL:
            return replace(finding, category=_CRITICAL)
        return finding

    def derive_findings_missed_by_ai(
        self,
        *,
        candidates: tuple[RadiologyFinding, ...],
        ai_findings: tuple[RadiologyFinding, ...],
    ) -> tuple[RadiologyFinding, ...]:
        known_text = " ".join(f.description.lower() for f in ai_findings)
        return tuple(
            candidate
            for candidate in candidates
            if candidate.category is _CRITICAL and candidate.description.lower() not in known_text
        )
