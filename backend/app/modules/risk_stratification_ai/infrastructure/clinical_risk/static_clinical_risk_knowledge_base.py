"""`StaticClinicalRiskKnowledgeBase` — the one concrete `ClinicalRiskPort`
implementation this task ships: a curated, necessarily-incomplete
keyword reference table covering the ten `RiskCategory` members with no
standardized public formula (every member except `NEWS2`/`MEWS`/
`QSOFA`/`SOFA_SIMPLIFIED`, which `StandardRiskScoringCalculator` computes
deterministically instead), the same "each module defines its own
local, necessarily-incomplete copy" precedent every prior AI module's
own knowledge-base adapter establishes for itself (most recently
`app.modules.drug_interaction_ai.infrastructure.interaction_knowledge
.static_drug_interaction_knowledge_base
.StaticDrugInteractionKnowledgeBase`). A real production system might
instead consult a licensed, comprehensive clinical risk-prediction
model; this is the pragmatic in-repo substitute.

Each category's rule set is matched against `diagnoses` + `medical_history`
(free-text keyword containment, case-insensitive), `current_medications`
(a separate keyword list, since a drug name is not a diagnosis), an
optional minimum `patient_age`, and — for `AKI_RISK` only — a curated
creatinine threshold scanned from `lab_values`. Returns `None` when no
rule for the given category matches anything in the given context,
rather than fabricating a risk factor.
"""

from dataclasses import dataclass

from app.modules.risk_stratification_ai.application.ports import ClinicalRiskPort
from app.modules.risk_stratification_ai.domain.enums import RiskCategory
from app.modules.risk_stratification_ai.domain.value_objects import LabValue, RiskScore

_AKI_CREATININE_THRESHOLD = 1.2


@dataclass(frozen=True)
class _CategoryRules:
    context_keywords: tuple[str, ...] = ()
    medication_keywords: tuple[str, ...] = ()
    min_age: int | None = None
    explanation: str = ""


_RULES: dict[RiskCategory, _CategoryRules] = {
    RiskCategory.SEPSIS_RISK: _CategoryRules(
        context_keywords=(
            "sepsis",
            "septic",
            "infection",
            "pneumonia",
            "urinary tract infection",
            "cellulitis",
            "bacteremia",
        ),
        explanation="Sepsis risk factors identified from diagnoses and medical history.",
    ),
    RiskCategory.AKI_RISK: _CategoryRules(
        context_keywords=(
            "chronic kidney disease",
            "acute kidney injury",
            "dehydration",
            "rhabdomyolysis",
        ),
        medication_keywords=("nsaid", "ace inhibitor", "vancomycin", "contrast", "diuretic"),
        explanation=(
            "Acute kidney injury risk factors identified from history, medications, or "
            "laboratory values."
        ),
    ),
    RiskCategory.RESPIRATORY_DETERIORATION: _CategoryRules(
        context_keywords=(
            "copd",
            "asthma",
            "pneumonia",
            "pulmonary embolism",
            "respiratory failure",
            "pulmonary edema",
        ),
        explanation=(
            "Respiratory deterioration risk factors identified from diagnoses and "
            "medical history."
        ),
    ),
    RiskCategory.CARDIOVASCULAR_RISK: _CategoryRules(
        context_keywords=(
            "coronary artery disease",
            "heart failure",
            "hypertension",
            "atrial fibrillation",
            "myocardial infarction",
            "cardiomyopathy",
        ),
        explanation="Cardiovascular risk factors identified from diagnoses and medical history.",
    ),
    RiskCategory.STROKE_RISK: _CategoryRules(
        context_keywords=(
            "atrial fibrillation",
            "hypertension",
            "diabetes",
            "prior stroke",
            "transient ischemic attack",
            "carotid stenosis",
        ),
        explanation="Stroke risk factors identified from diagnoses and medical history.",
    ),
    RiskCategory.BLEEDING_RISK: _CategoryRules(
        context_keywords=("peptic ulcer", "bleeding disorder", "thrombocytopenia"),
        medication_keywords=(
            "warfarin",
            "aspirin",
            "clopidogrel",
            "heparin",
            "apixaban",
            "rivaroxaban",
        ),
        explanation="Bleeding risk factors identified from history and current medications.",
    ),
    RiskCategory.FALL_RISK: _CategoryRules(
        context_keywords=("fall", "gait instability", "osteoporosis", "vertigo"),
        medication_keywords=("benzodiazepine", "sedative", "opioid", "hypnotic"),
        min_age=65,
        explanation="Fall risk factors identified from history, current medications, or age.",
    ),
    RiskCategory.READMISSION_RISK: _CategoryRules(
        context_keywords=(
            "heart failure",
            "copd",
            "chronic kidney disease",
            "frequent admission",
            "non-adherence",
        ),
        explanation="Readmission risk factors identified from diagnoses and medical history.",
    ),
    RiskCategory.MORTALITY_RISK: _CategoryRules(
        context_keywords=(
            "metastatic cancer",
            "end-stage",
            "multi-organ failure",
            "do not resuscitate",
            "palliative",
        ),
        explanation="Mortality risk factors identified from diagnoses and medical history.",
    ),
    RiskCategory.GENERAL_CLINICAL_DETERIORATION: _CategoryRules(
        context_keywords=(
            "frailty",
            "failure to thrive",
            "multiple comorbidities",
            "functional decline",
        ),
        min_age=80,
        explanation="General clinical deterioration risk factors identified from history or age.",
    ),
}


class StaticClinicalRiskKnowledgeBase(ClinicalRiskPort):
    def identify_risk_factors(
        self,
        category: RiskCategory,
        *,
        diagnoses: tuple[str, ...],
        medical_history: tuple[str, ...],
        current_medications: tuple[str, ...],
        lab_values: tuple[LabValue, ...],
        patient_age: int | None,
    ) -> RiskScore | None:
        rules = _RULES.get(category)
        if rules is None:
            return None

        factors: list[str] = []
        for text in diagnoses + medical_history:
            normalized = text.strip().lower()
            for keyword in rules.context_keywords:
                if keyword in normalized:
                    factors.append(text.strip())
                    break
        for medication in current_medications:
            normalized = medication.strip().lower()
            for keyword in rules.medication_keywords:
                if keyword in normalized:
                    factors.append(f"Current medication: {medication.strip()}")
                    break
        if rules.min_age is not None and patient_age is not None and patient_age >= rules.min_age:
            factors.append(f"Patient age {patient_age} (>= {rules.min_age})")
        if category is RiskCategory.AKI_RISK:
            creatinine_factor = self._check_creatinine(lab_values)
            if creatinine_factor is not None:
                factors.append(creatinine_factor)

        if not factors:
            return None
        deduped = tuple(dict.fromkeys(factors))
        return RiskScore(
            category=category,
            score_value=None,
            contributing_factors=deduped,
            clinical_explanation=rules.explanation,
        )

    def _check_creatinine(self, lab_values: tuple[LabValue, ...]) -> str | None:
        for lab in lab_values:
            if "creatinine" not in lab.test_name.strip().lower() or lab.numeric_value is None:
                continue
            if lab.numeric_value >= _AKI_CREATININE_THRESHOLD:
                return f"Elevated creatinine {lab.numeric_value:g}"
        return None
