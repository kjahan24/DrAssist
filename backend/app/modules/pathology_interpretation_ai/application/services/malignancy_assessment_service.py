"""`MalignancyAssessmentService` — this task's own explicitly-named
APPLICATION service, and the safety-net half of the `ClinicalCorrelationPort`
seam (see that port's own docstring).

The AI's own `PathologyFinding.category` classification is trusted by
default, but this service applies two independent, deterministic
cross-checks against it, the same "AI-reported plus a deterministic
floor/override, merged" enrichment shape
`app.modules.radiology_interpretation_ai.application.services
.critical_finding_detection_service.CriticalFindingDetectionService`
establishes for its own module, applied here for patient-safety reasons
specific to pathology interpretation:

- `escalate_on_malignant_keywords` — re-classifies each AI-reported
  finding's own description via `ClinicalCorrelationPort
  .classify_description`; when the port recognizes malignant language
  the AI itself did not flag as such, the finding's category is
  escalated. This catches a *severity misclassification* (the AI found
  it, but under-called its significance).
- `derive_findings_missed_by_ai` — given the deterministic candidate
  pool `application/services/finding_extraction_service
  .FindingExtractionService.extract` already produced for this same
  report (passed in, not re-derived here — the use case computes that
  pool exactly once), appends any malignant-category candidate whose
  keyword phrase does not already appear (case-insensitively) inside any
  AI-reported finding's description. This catches an *omission* (the AI
  never mentioned it at all) — a deliberately simple, deterministic
  case-insensitive substring containment check rather than fuzzy NLP
  matching, since a real malignant-keyword phrase either appears in the
  AI's own wording or it does not.
"""

from dataclasses import replace

from app.modules.pathology_interpretation_ai.application.ports import ClinicalCorrelationPort
from app.modules.pathology_interpretation_ai.domain.enums import PathologyFindingCategory
from app.modules.pathology_interpretation_ai.domain.value_objects import PathologyFinding

_MALIGNANT = PathologyFindingCategory.MALIGNANT


class MalignancyAssessmentService:
    def __init__(self, *, correlator: ClinicalCorrelationPort) -> None:
        self._correlator = correlator

    def has_malignant_findings(self, findings: tuple[PathologyFinding, ...]) -> bool:
        return any(finding.category is _MALIGNANT for finding in findings)

    def escalate_on_malignant_keywords(
        self, findings: tuple[PathologyFinding, ...]
    ) -> tuple[PathologyFinding, ...]:
        return tuple(self._maybe_escalate(finding) for finding in findings)

    def _maybe_escalate(self, finding: PathologyFinding) -> PathologyFinding:
        if finding.category is _MALIGNANT:
            return finding
        deterministic_category = self._correlator.classify_description(finding.description)
        if deterministic_category is _MALIGNANT:
            return replace(finding, category=_MALIGNANT)
        return finding

    def derive_findings_missed_by_ai(
        self,
        *,
        candidates: tuple[PathologyFinding, ...],
        ai_findings: tuple[PathologyFinding, ...],
    ) -> tuple[PathologyFinding, ...]:
        known_text = " ".join(f.description.lower() for f in ai_findings)
        return tuple(
            candidate
            for candidate in candidates
            if candidate.category is _MALIGNANT and candidate.description.lower() not in known_text
        )
