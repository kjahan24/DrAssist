"""`StaticDrugInteractionKnowledgeBase`/`StaticInteractionEvidenceKnowledgeBase`
— the two concrete port implementations this task ships for
`DrugInteractionPort`/`InteractionEvidencePort`: a small, curated table
of well-known drug-drug interaction pairs. A real production system
might instead consult a licensed, comprehensive drug-interaction
database here; this module's own small, table-driven implementation is
the pragmatic in-repo substitute, the same "each module defines its own
local, necessarily-incomplete copy" precedent every prior AI module's
own knowledge-base adapter establishes for itself.

Both classes share the same private `_KNOWN_INTERACTIONS` table rather
than each keeping an independent copy of the same pair data — the two
ports serve genuinely different purposes (existence/severity detection
vs. evidence-level classification), so two distinct adapter classes are
still warranted, but there is exactly one definition of *which pairs are
known and what is known about them*, per this task's own "Avoid
duplicate implementations" rule.

Drug names are matched case-insensitively against `drug_name` only (not
`generic_name`/`brand_name`) — a deliberately simple, table-key-based
match consistent with the "each module defines its own local,
necessarily-incomplete copy" precedent's own scope.
"""

from dataclasses import dataclass

from app.modules.drug_interaction_ai.application.ports import (
    DrugInteractionPort,
    InteractionEvidencePort,
)
from app.modules.drug_interaction_ai.domain.enums import (
    EvidenceLevel,
    SafetyIssueCategory,
    SafetySeverity,
)
from app.modules.drug_interaction_ai.domain.value_objects import SafetyIssue

_DRUG_DRUG = SafetyIssueCategory.DRUG_DRUG_INTERACTION


@dataclass(frozen=True, slots=True)
class _InteractionData:
    severity: SafetySeverity
    mechanism: str
    clinical_significance: str
    evidence_level: EvidenceLevel


_KNOWN_INTERACTIONS: dict[frozenset[str], _InteractionData] = {
    frozenset({"warfarin", "aspirin"}): _InteractionData(
        severity=SafetySeverity.MAJOR,
        mechanism="Additive anticoagulant and antiplatelet effects.",
        clinical_significance="Substantially increased risk of major bleeding.",
        evidence_level=EvidenceLevel.ESTABLISHED,
    ),
    frozenset({"warfarin", "ibuprofen"}): _InteractionData(
        severity=SafetySeverity.MAJOR,
        mechanism="NSAID-induced platelet inhibition combined with anticoagulation.",
        clinical_significance="Increased risk of gastrointestinal and other bleeding.",
        evidence_level=EvidenceLevel.ESTABLISHED,
    ),
    frozenset({"simvastatin", "clarithromycin"}): _InteractionData(
        severity=SafetySeverity.MAJOR,
        mechanism="CYP3A4 inhibition increases statin levels.",
        clinical_significance="Raised risk of myopathy and rhabdomyolysis.",
        evidence_level=EvidenceLevel.ESTABLISHED,
    ),
    frozenset({"sildenafil", "nitroglycerin"}): _InteractionData(
        severity=SafetySeverity.CONTRAINDICATED,
        mechanism="Additive vasodilation.",
        clinical_significance="Risk of severe, potentially fatal hypotension.",
        evidence_level=EvidenceLevel.ESTABLISHED,
    ),
    frozenset({"phenelzine", "sertraline"}): _InteractionData(
        severity=SafetySeverity.CONTRAINDICATED,
        mechanism="Combined MAOI and SSRI serotonergic activity.",
        clinical_significance="Risk of life-threatening serotonin syndrome.",
        evidence_level=EvidenceLevel.ESTABLISHED,
    ),
    frozenset({"lisinopril", "spironolactone"}): _InteractionData(
        severity=SafetySeverity.MODERATE,
        mechanism="Combined renin-angiotensin blockade and potassium-sparing diuresis.",
        clinical_significance="Increased risk of hyperkalemia.",
        evidence_level=EvidenceLevel.PROBABLE,
    ),
    frozenset({"digoxin", "amiodarone"}): _InteractionData(
        severity=SafetySeverity.MAJOR,
        mechanism="Amiodarone reduces digoxin clearance.",
        clinical_significance="Raised digoxin levels and toxicity risk.",
        evidence_level=EvidenceLevel.ESTABLISHED,
    ),
    frozenset({"clopidogrel", "omeprazole"}): _InteractionData(
        severity=SafetySeverity.MODERATE,
        mechanism="CYP2C19 inhibition may reduce clopidogrel activation.",
        clinical_significance="Potentially reduced antiplatelet effect.",
        evidence_level=EvidenceLevel.SUSPECTED,
    ),
}


def _lookup(drug_a: str, drug_b: str) -> _InteractionData | None:
    return _KNOWN_INTERACTIONS.get(frozenset({drug_a.strip().lower(), drug_b.strip().lower()}))


class StaticDrugInteractionKnowledgeBase(DrugInteractionPort):
    def check_pairwise_interaction(self, drug_a: str, drug_b: str) -> SafetyIssue | None:
        data = _lookup(drug_a, drug_b)
        if data is None:
            return None
        return SafetyIssue(
            category=_DRUG_DRUG,
            description=f"Interaction between {drug_a} and {drug_b}.",
            severity=data.severity,
            mechanism=data.mechanism,
            clinical_significance=data.clinical_significance,
            evidence_level=data.evidence_level,
            involved_medications=(drug_a, drug_b),
        )


class StaticInteractionEvidenceKnowledgeBase(InteractionEvidencePort):
    def classify_evidence_level(self, drug_a: str, drug_b: str) -> EvidenceLevel | None:
        data = _lookup(drug_a, drug_b)
        return data.evidence_level if data is not None else None
