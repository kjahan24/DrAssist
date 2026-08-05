"""Enums owned by the AI Drug Interaction & Medication Safety module's
domain."""

from enum import StrEnum


class DrugInteractionSetting(StrEnum):
    """Drives prompt selection (`infrastructure/prompts/
    template_selector.py`) — each setting has its own independently-
    versioned prompt template set. Seven members, in the same order, as
    this task's own PROMPTS section — the richest settings vocabulary of
    any AI module in this codebase so far (every prior module's own
    setting enum has five members; this one adds "icu" and "pregnancy"
    on top of the usual outpatient/inpatient/emergency/pediatric/
    geriatric set, and drops none of them)."""

    OUTPATIENT = "outpatient"
    INPATIENT = "inpatient"
    EMERGENCY = "emergency"
    ICU = "icu"
    PEDIATRIC = "pediatric"
    GERIATRIC = "geriatric"
    PREGNANCY = "pregnancy"


class DrugInteractionOutputFormat(StrEnum):
    """What shape a result is rendered into."""

    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"


class SafetyIssueCategory(StrEnum):
    """The closed vocabulary this task's own DETECT section names, in
    the same order — eighteen categories, every one of them represented
    on a single `SafetyIssue.category` tag rather than eighteen
    separately-tracked collections, the same "one unified, tagged
    collection" precedent
    `app.modules.radiology_interpretation_ai.domain.enums
    .RadiologyFindingCategory`/`app.modules.pathology_interpretation_ai
    .domain.enums.PathologyFindingCategory` establish for their own,
    smaller category sets. Unlike those two modules, this task's own
    OUTPUT section does not ask for a filtered/computed view per
    category (no "Drug-Drug Interactions" / "Bleeding Risk" / etc. OUTPUT
    field of its own) — only the flat "Interaction List" — so
    `DrugInteractionAnalysisResult` exposes no per-category computed
    properties; `category` exists purely so each `SafetyIssue` records
    *which* of the eighteen DETECT concerns it represents."""

    DRUG_DRUG_INTERACTION = "drug_drug_interaction"
    DRUG_ALLERGY_INTERACTION = "drug_allergy_interaction"
    DRUG_DISEASE_INTERACTION = "drug_disease_interaction"
    DUPLICATE_THERAPY = "duplicate_therapy"
    CONTRAINDICATION = "contraindication"
    BLACK_BOX_WARNING = "black_box_warning"
    QT_PROLONGATION_RISK = "qt_prolongation_risk"
    SEROTONIN_SYNDROME_RISK = "serotonin_syndrome_risk"
    BLEEDING_RISK = "bleeding_risk"
    NEPHROTOXICITY_RISK = "nephrotoxicity_risk"
    HEPATOTOXICITY_RISK = "hepatotoxicity_risk"
    MEDICATION_RECONCILIATION_ISSUE = "medication_reconciliation_issue"
    HIGH_RISK_ELDERLY_MEDICATION = "high_risk_elderly_medication"
    PEDIATRIC_DOSE_SAFETY = "pediatric_dose_safety"
    PREGNANCY_SAFETY = "pregnancy_safety"
    LACTATION_SAFETY = "lactation_safety"
    RENAL_DOSE_ADJUSTMENT = "renal_dose_adjustment"
    HEPATIC_DOSE_ADJUSTMENT = "hepatic_dose_adjustment"


class SafetySeverity(StrEnum):
    """The closed vocabulary this task's own "Interaction Severity"
    OUTPUT field needs — a standard four-level clinical drug-interaction
    severity scale (the same shape common drug-interaction references
    such as Lexicomp/Micromedex use), ordered least to most severe."""

    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CONTRAINDICATED = "contraindicated"


class EvidenceLevel(StrEnum):
    """The closed vocabulary this task's own "Evidence Level" OUTPUT
    field needs — a standard four-level pharmacology evidence-grading
    scale, ordered strongest to weakest."""

    ESTABLISHED = "established"
    PROBABLE = "probable"
    SUSPECTED = "suspected"
    THEORETICAL = "theoretical"


class SafetyAnalysisStatus(StrEnum):
    """Recorded on `GenerationSession` for this task's own AUDIT "safety
    analysis status" field — named to match that wording exactly, the
    same reasoning every prior AI module's own status enum documents for
    itself."""

    COMPLETED = "completed"
    FAILED = "failed"


class PregnancyStatus(StrEnum):
    """A same-shaped local copy of
    `app.modules.pathology_interpretation_ai.domain.enums
    .PregnancyStatus` — pregnancy status is explicitly named in this
    task's own SUPPORTED INPUT section."""

    NOT_PREGNANT = "not_pregnant"
    PREGNANT = "pregnant"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class LactationStatus(StrEnum):
    """A same-*shaped* new enum (no prior AI module's own INPUT section
    named "Lactation status" before this task) — lactation status is
    explicitly named in this task's own SUPPORTED INPUT section,
    alongside pregnancy status, and given the identical four-member
    treatment for consistency."""

    LACTATING = "lactating"
    NOT_LACTATING = "not_lactating"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
