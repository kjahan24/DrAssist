"""`DefaultClinicalReasoningAdvisor` — the one concrete
`ClinicalReasoningPort` implementation this task ships. See that port's
own docstring (`application/ports.py`) for the full split between what
it computes deterministically and what remains the AI's own semantic
judgment.

`classify_minimum_urgency` is a simple, defensible rule: a candidate with
no red-flag indicators has a deterministic floor of `UrgencyLevel.ROUTINE`
(confidence alone never manufactures urgency). A candidate carrying one
or more red-flag indicators is never classified below `UrgencyLevel
.URGENT` — a red flag is itself a signal that the diagnosis, if correct,
cannot safely wait — and is raised further to `UrgencyLevel.EMERGENT`
when the model is also highly confident in that candidate, since a red
flag the model is *sure* about warrants more immediate attention than
one it is only tentatively raising.

`identify_missing_information` flags clinical-evidence categories that
materially affect differential-diagnosis quality when absent — a real
production system might instead consult a structured "required evidence
by presentation" knowledge base; this module's own small, rule-based
implementation is the pragmatic in-repo substitute, the same "each
module defines its own local, necessarily-incomplete copy" precedent
`app.modules.prescription_ai.infrastructure.knowledge
.medication_knowledge_base.StaticMedicationKnowledgeBase` already
establishes for its own module.
"""

from app.modules.differential_diagnosis_ai.application.ports import ClinicalReasoningPort
from app.modules.differential_diagnosis_ai.domain.enums import UrgencyLevel
from app.modules.differential_diagnosis_ai.domain.value_objects import DifferentialDiagnosisInput

_HIGH_CONFIDENCE_THRESHOLD = 0.7


class DefaultClinicalReasoningAdvisor(ClinicalReasoningPort):
    def classify_minimum_urgency(
        self, *, red_flag_indicators: tuple[str, ...], confidence_score: float | None
    ) -> UrgencyLevel:
        if not red_flag_indicators:
            return UrgencyLevel.ROUTINE
        if confidence_score is not None and confidence_score >= _HIGH_CONFIDENCE_THRESHOLD:
            return UrgencyLevel.EMERGENT
        return UrgencyLevel.URGENT

    def identify_missing_information(self, evidence: DifferentialDiagnosisInput) -> tuple[str, ...]:
        missing: list[str] = []

        has_narrative_content = bool(
            (evidence.history_of_present_illness or "").strip()
            or evidence.symptoms
            or (evidence.review_of_systems or "").strip()
        )
        if not has_narrative_content:
            missing.append(
                "no HPI, symptoms, or review of systems provided — differential quality "
                "depends heavily on the presenting narrative"
            )

        has_objective_content = bool(
            (evidence.physical_examination or "").strip() or evidence.vitals
        )
        if not has_objective_content:
            missing.append("no physical examination findings or vitals provided")

        if not evidence.laboratory_results and not (evidence.imaging_summary or "").strip():
            missing.append(
                "no laboratory results or imaging summary provided — some diagnoses cannot "
                "be meaningfully ranked without objective data"
            )

        return tuple(missing)
