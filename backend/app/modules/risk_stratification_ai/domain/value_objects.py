"""Value objects for the AI Risk Stratification & Early Warning Score
module's domain.

None of these reference another module's `domain`/`application`/
`infrastructure` type — every cross-module identity (organization,
patient) is a plain `UUID`, and clinical content is exactly what this
task's own SUPPORTED INPUT specification calls for: values the caller
supplies directly, the same "explicit encounter input only" design every
prior AI module's own value-objects module docstring establishes for
itself. `laboratory_interpretation`, `radiology_interpretation`,
`pathology_interpretation`, and `medical_reasoning_context` are plain
`str | None` fields — this module never calls into any of those four
peer modules' own generation pipelines directly; the caller supplies
whatever already-generated summary text it wants considered, the same
"explicit input, not a live cross-module lookup" design
`app.modules.drug_interaction_ai.domain.value_objects
.DrugInteractionAnalysisInput`'s own `laboratory_interpretation`/
`radiology_interpretation` fields establish for themselves (see
`container.py`'s own scope note for the one genuine cross-module *port*
dependency this module does have —
`MedicalReasoningAIPort.score_confidence` — which is a use-case-level
concern, not a domain one).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from app.modules.risk_stratification_ai.domain.enums import (
    ConsciousnessLevel,
    OverallRiskLevel,
    RiskAnalysisStatus,
    RiskCategory,
    RiskStratificationOutputFormat,
    RiskStratificationSetting,
)
from app.modules.risk_stratification_ai.domain.exceptions import (
    IncompleteLaboratoryValueError,
    InvalidRiskStratificationInputError,
    MissingVitalSignsError,
)
from app.shared.domain.value_object import ValueObject

_MAX_PLAUSIBLE_AGE = 150
_MAX_PLAUSIBLE_RESPIRATORY_RATE = 100
_MAX_PLAUSIBLE_HEART_RATE = 300
_MIN_PLAUSIBLE_TEMPERATURE_C = 25.0
_MAX_PLAUSIBLE_TEMPERATURE_C = 45.0


@dataclass(frozen=True, slots=True)
class VitalSigns(ValueObject):
    """One set of vital sign readings — every field is optional so a
    caller can supply whatever subset it actually has, but at least one
    must be present (see `RiskStratificationInput.__post_init__`'s own
    "missing vital signs" check); individual standardized-score
    computations (`infrastructure/clinical_scoring
    /standard_risk_scoring_calculator.py`) each separately require their
    own full parameter set and return `None` rather than a misleading
    partial score when theirs is incomplete."""

    respiratory_rate: int | None = None
    oxygen_saturation: float | None = None
    on_supplemental_oxygen: bool | None = None
    temperature_celsius: float | None = None
    systolic_bp: int | None = None
    diastolic_bp: int | None = None
    heart_rate: int | None = None
    consciousness_level: ConsciousnessLevel | None = None

    def __post_init__(self) -> None:
        if self.respiratory_rate is not None and not (
            0 <= self.respiratory_rate <= _MAX_PLAUSIBLE_RESPIRATORY_RATE
        ):
            raise InvalidRiskStratificationInputError(
                f"respiratory_rate must be between 0 and {_MAX_PLAUSIBLE_RESPIRATORY_RATE}"
            )
        if self.oxygen_saturation is not None and not (0 <= self.oxygen_saturation <= 100):
            raise InvalidRiskStratificationInputError("oxygen_saturation must be between 0 and 100")
        if self.temperature_celsius is not None and not (
            _MIN_PLAUSIBLE_TEMPERATURE_C <= self.temperature_celsius <= _MAX_PLAUSIBLE_TEMPERATURE_C
        ):
            raise InvalidRiskStratificationInputError(
                "temperature_celsius must be between "
                f"{_MIN_PLAUSIBLE_TEMPERATURE_C} and {_MAX_PLAUSIBLE_TEMPERATURE_C}"
            )
        if self.systolic_bp is not None and self.systolic_bp < 0:
            raise InvalidRiskStratificationInputError("systolic_bp must not be negative")
        if self.diastolic_bp is not None and self.diastolic_bp < 0:
            raise InvalidRiskStratificationInputError("diastolic_bp must not be negative")
        if self.heart_rate is not None and not (0 <= self.heart_rate <= _MAX_PLAUSIBLE_HEART_RATE):
            raise InvalidRiskStratificationInputError(
                f"heart_rate must be between 0 and {_MAX_PLAUSIBLE_HEART_RATE}"
            )

    @property
    def is_empty(self) -> bool:
        return (
            self.respiratory_rate is None
            and self.oxygen_saturation is None
            and self.on_supplemental_oxygen is None
            and self.temperature_celsius is None
            and self.systolic_bp is None
            and self.diastolic_bp is None
            and self.heart_rate is None
            and self.consciousness_level is None
        )


@dataclass(frozen=True, slots=True)
class LabValue(ValueObject):
    """One caller-supplied laboratory result — a same-shaped, smaller
    local copy of `app.modules.lab_interpretation_ai.domain.value_objects
    .LabValue` (domain code never imports a peer module's domain type):
    this module only needs a test name, its reported value, and an
    optional parsed numeric form to support `SOFA_SIMPLIFIED`'s renal
    component and the ten AI-assessed risk categories' own deterministic
    risk-factor lookups (see `infrastructure/clinical_risk
    /static_clinical_risk_knowledge_base.py`) — reference ranges and
    units are out of scope here."""

    test_name: str
    value: str | None = None
    numeric_value: float | None = None

    def __post_init__(self) -> None:
        if not self.test_name.strip():
            raise InvalidRiskStratificationInputError("test_name must not be blank")
        if (self.value is None or not self.value.strip()) and self.numeric_value is None:
            raise IncompleteLaboratoryValueError(self.test_name)


@dataclass(frozen=True, slots=True)
class RiskStratificationInput(ValueObject):
    organization_id: UUID
    patient_id: UUID
    risk_setting: RiskStratificationSetting
    vital_signs: VitalSigns
    lab_values: tuple[LabValue, ...] = ()
    patient_age: int | None = None
    medical_history: tuple[str, ...] = ()
    diagnoses: tuple[str, ...] = ()
    current_medications: tuple[str, ...] = ()
    allergies: tuple[str, ...] = ()
    clinical_notes: tuple[str, ...] = ()
    soap_notes: tuple[str, ...] = ()
    laboratory_interpretation: str | None = None
    radiology_interpretation: str | None = None
    pathology_interpretation: str | None = None
    medical_reasoning_context: str | None = None
    language: str = "en"
    output_format: RiskStratificationOutputFormat = RiskStratificationOutputFormat.JSON

    def __post_init__(self) -> None:
        if self.vital_signs.is_empty:
            raise MissingVitalSignsError()
        if not self.language.strip():
            raise InvalidRiskStratificationInputError("language must not be blank")
        if self.patient_age is not None and not (0 <= self.patient_age <= _MAX_PLAUSIBLE_AGE):
            raise InvalidRiskStratificationInputError(
                f"patient_age must be between 0 and {_MAX_PLAUSIBLE_AGE} when given"
            )


@dataclass(frozen=True, slots=True)
class RiskScore(ValueObject):
    """One assessed risk — `category` tags which of this task's own
    fourteen ASSESS concerns it represents, and `score_value`/
    `contributing_factors`/`clinical_explanation` are exactly this
    task's own "Risk Scores"/"Contributing Factors"/"Clinical
    Explanation" OUTPUT sub-fields, applied uniformly to every category:
    `score_value` is populated with the computed total for the four
    standardized scores (`NEWS2`/`MEWS`/`QSOFA`/`SOFA_SIMPLIFIED`) and
    left `None` for the ten AI-assessed categories unless the AI itself
    (or a future deterministic model) reports a numeric risk index for
    one of them."""

    category: RiskCategory
    score_value: float | None
    contributing_factors: tuple[str, ...]
    clinical_explanation: str


@dataclass(frozen=True, slots=True)
class RiskStratificationResult(ValueObject):
    """The canonical, structured risk-stratification result — always
    populated regardless of `output_format` (a rendering-time concern),
    the same "generation produces structure; rendering produces
    presentation" split every prior AI module's own result value object
    establishes for itself."""

    overall_risk_level: OverallRiskLevel
    risk_scores: tuple[RiskScore, ...]
    early_warning_indicators: tuple[str, ...]
    recommended_monitoring: tuple[str, ...]
    suggested_escalation: tuple[str, ...]
    suggested_follow_up: tuple[str, ...]
    red_flag_alerts: tuple[str, ...]
    clinical_reasoning: str
    confidence_score: float | None
    raw_text: str
    output_format: RiskStratificationOutputFormat

    @property
    def is_empty(self) -> bool:
        return (
            not self.risk_scores
            and not self.early_warning_indicators
            and not self.recommended_monitoring
            and not self.suggested_escalation
            and not self.suggested_follow_up
            and not self.red_flag_alerts
            and not self.clinical_reasoning.strip()
        )


@dataclass(frozen=True, slots=True)
class RiskStratificationTemplateSet(ValueObject):
    """The three AI-Foundation-registered prompt template names (system/
    developer/user) and pinned version
    `RiskStratificationTemplateSelectorPort.select` resolves a
    `RiskStratificationSetting` to."""

    system_template_name: str
    developer_template_name: str
    user_template_name: str
    version: int


@dataclass(frozen=True, slots=True)
class GenerationSession(ValueObject):
    """The tracked record of one risk-analysis attempt, per this task's
    own "AUDIT — provider, model, latency, token usage, risk analysis
    status" requirement. `risk_setting` is carried beyond the literal
    AUDIT list, the same "each session also carries its own setting/
    language" precedent every prior AI module's own `GenerationSession`
    establishes for itself."""

    generation_id: UUID
    provider: str
    model: str
    risk_setting: str
    language: str
    status: RiskAnalysisStatus
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class RiskStratificationStreamChunk(ValueObject):
    """One increment of a streamed generation — a post-hoc chunking of
    one complete AI Foundation call, the same shape every prior AI
    module's own stream chunk value object establishes for itself."""

    delta: str
    is_final: bool = False
