"""`DrugInteractionService` — this task's own explicitly-named
APPLICATION service, covering "Drug-Drug Interactions" detection (the
first of this task's own eighteen DETECT categories) and the evidence-
grading safety net for it.

- `detect_known_interactions` — checks every unique pair drawn from
  `current_medications` + `new_prescription` (when present) against
  `DrugInteractionPort.check_pairwise_interaction`, the same
  deterministic-detection role every prior AI module's own knowledge-
  base-backed service plays for itself.
- `reconcile_evidence_levels` — the safety-net half: for every
  `SafetyIssueCategory.DRUG_DRUG_INTERACTION` issue (AI-reported or
  deterministically detected) that names at least two
  `involved_medications`, verifies/backfills its `evidence_level` via
  `InteractionEvidencePort.classify_evidence_level` — the same
  "AI-reported plus a deterministic floor/override, merged" enrichment
  shape `app.modules.pathology_interpretation_ai.application.services
  .malignancy_assessment_service.MalignancyAssessmentService
  .escalate_on_malignant_keywords` establishes for its own module,
  applied here to evidence grading rather than category escalation: a
  curated evidence level always overrides an AI-reported one (curated
  reference data is more trustworthy than an unverified AI claim), and
  a missing AI-reported evidence level is backfilled from curated data
  when available.
"""

from dataclasses import replace
from itertools import combinations

from app.modules.drug_interaction_ai.application.ports import (
    DrugInteractionPort,
    InteractionEvidencePort,
)
from app.modules.drug_interaction_ai.domain.enums import SafetyIssueCategory
from app.modules.drug_interaction_ai.domain.value_objects import MedicationEntry, SafetyIssue

_DRUG_DRUG = SafetyIssueCategory.DRUG_DRUG_INTERACTION


class DrugInteractionService:
    def __init__(
        self, *, interaction_port: DrugInteractionPort, evidence_port: InteractionEvidencePort
    ) -> None:
        self._interaction_port = interaction_port
        self._evidence_port = evidence_port

    def detect_known_interactions(
        self, medications: tuple[MedicationEntry, ...]
    ) -> tuple[SafetyIssue, ...]:
        issues: list[SafetyIssue] = []
        for drug_a, drug_b in combinations(medications, 2):
            issue = self._interaction_port.check_pairwise_interaction(
                drug_a.drug_name, drug_b.drug_name
            )
            if issue is not None:
                issues.append(issue)
        return tuple(issues)

    def reconcile_evidence_levels(self, issues: tuple[SafetyIssue, ...]) -> tuple[SafetyIssue, ...]:
        return tuple(self._maybe_reconcile(issue) for issue in issues)

    def _maybe_reconcile(self, issue: SafetyIssue) -> SafetyIssue:
        if issue.category is not _DRUG_DRUG or len(issue.involved_medications) < 2:
            return issue
        curated_level = self._evidence_port.classify_evidence_level(
            issue.involved_medications[0], issue.involved_medications[1]
        )
        if curated_level is None or curated_level == issue.evidence_level:
            return issue
        return replace(issue, evidence_level=curated_level)
