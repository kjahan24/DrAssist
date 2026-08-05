"""Enums owned by the AI Risk Stratification & Early Warning Score
module's domain."""

from enum import StrEnum


class RiskStratificationSetting(StrEnum):
    """Drives prompt selection (`infrastructure/prompts/
    template_selector.py`) — each setting has its own independently-
    versioned prompt template set. Six members, in the same order, as
    this task's own PROMPTS section (emergency/inpatient/icu/outpatient/
    pediatric/geriatric) — a distinct ordering from every prior AI
    module's own setting enum (which always lists "outpatient" first),
    the direct reading of this task's own PROMPTS list."""

    EMERGENCY = "emergency"
    INPATIENT = "inpatient"
    ICU = "icu"
    OUTPATIENT = "outpatient"
    PEDIATRIC = "pediatric"
    GERIATRIC = "geriatric"


class RiskStratificationOutputFormat(StrEnum):
    """What shape a result is rendered into."""

    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"


class RiskCategory(StrEnum):
    """The closed vocabulary this task's own ASSESS section names, in
    the same order — fourteen categories, every one of them represented
    on a single `RiskScore.category` tag rather than fourteen
    separately-tracked collections, the same "one unified, tagged
    collection" precedent
    `app.modules.drug_interaction_ai.domain.enums.SafetyIssueCategory`
    establishes for its own, similarly large category set. The first
    four (`NEWS2`, `MEWS`, `QSOFA`, `SOFA_SIMPLIFIED`) are standardized,
    deterministically-computable clinical scores (see
    `infrastructure/clinical_scoring/standard_risk_scoring_calculator
    .py`); the remaining ten are AI-assessed risk categories with a
    deterministic risk-factor safety net (see `infrastructure
    /clinical_risk/static_clinical_risk_knowledge_base.py`)."""

    NEWS2 = "news2"
    MEWS = "mews"
    QSOFA = "qsofa"
    SOFA_SIMPLIFIED = "sofa_simplified"
    SEPSIS_RISK = "sepsis_risk"
    AKI_RISK = "aki_risk"
    RESPIRATORY_DETERIORATION = "respiratory_deterioration"
    CARDIOVASCULAR_RISK = "cardiovascular_risk"
    STROKE_RISK = "stroke_risk"
    BLEEDING_RISK = "bleeding_risk"
    FALL_RISK = "fall_risk"
    READMISSION_RISK = "readmission_risk"
    MORTALITY_RISK = "mortality_risk"
    GENERAL_CLINICAL_DETERIORATION = "general_clinical_deterioration"


class OverallRiskLevel(StrEnum):
    """The closed vocabulary this task's own "Overall Risk Level" OUTPUT
    field needs — a standard four-level clinical risk scale, ordered
    least to most severe."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class ConsciousnessLevel(StrEnum):
    """The AVPU scale (Alert, Voice, Pain, Unresponsive) — the standard
    rapid consciousness assessment NEWS2/MEWS/qSOFA all draw on, and part
    of this task's own "Vital signs" SUPPORTED INPUT."""

    ALERT = "alert"
    VOICE = "voice"
    PAIN = "pain"
    UNRESPONSIVE = "unresponsive"


class RiskAnalysisStatus(StrEnum):
    """Recorded on `GenerationSession` for this task's own AUDIT "risk
    analysis status" field — named to match that wording exactly, the
    same reasoning every prior AI module's own status enum documents for
    itself."""

    COMPLETED = "completed"
    FAILED = "failed"
