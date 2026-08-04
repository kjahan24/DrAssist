"""Value objects for the AI Differential Diagnosis module's domain.

None of these reference another module's `domain`/`application`/
`infrastructure` type — every cross-module identity (organization,
patient, visit) is a plain `UUID`, and clinical content (chief complaint,
HPI, symptoms, ROS, physical exam, vitals, laboratory results, imaging
summary, clinical/SOAP note text, ICD-10 suggestions, prescription
suggestions, allergies, medical conditions) is exactly what the task's
own INPUT specification calls for: values the caller supplies directly,
not records looked up from the Clinical Note AI/SOAP Note AI/ICD-10 AI/
Prescription AI modules. This module never queries another module's
public port — its entire input is self-contained clinical context, the
same design `app.modules.prescription_ai.domain.value_objects`
establishes for itself (see that module's own module docstring for the
full reasoning, which applies identically here). `icd10_suggestions` and
`prescription_suggestions` are tuples of plain strings supplied by the
caller — a caller that already ran `app.modules.icd10_ai`'s
`generate_suggestions` or `app.modules.prescription_ai`'s
`generate_suggestion` passes those results through as text here, the
same way `app.modules.prescription_ai.domain.value_objects
.PrescriptionContextInput.icd10_suggestions` does for itself.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from app.modules.differential_diagnosis_ai.domain.enums import (
    ClinicalSetting,
    DifferentialOutputFormat,
    GenerationStatus,
    PatientSex,
    PregnancyStatus,
    UrgencyLevel,
)
from app.modules.differential_diagnosis_ai.domain.exceptions import InvalidClinicalEvidenceError
from app.shared.domain.value_object import ValueObject

_MAX_PLAUSIBLE_AGE = 150


@dataclass(frozen=True, slots=True)
class DifferentialDiagnosisInput(ValueObject):
    organization_id: UUID
    patient_id: UUID
    chief_complaint: str
    clinical_setting: ClinicalSetting
    language: str = "en"
    visit_id: UUID | None = None
    history_of_present_illness: str | None = None
    symptoms: tuple[str, ...] = ()
    review_of_systems: str | None = None
    physical_examination: str | None = None
    vitals: Mapping[str, str] = field(default_factory=dict)
    laboratory_results: tuple[str, ...] = ()
    imaging_summary: str | None = None
    clinical_note: str | None = None
    soap_note: str | None = None
    icd10_suggestions: tuple[str, ...] = ()
    prescription_suggestions: tuple[str, ...] = ()
    allergies: tuple[str, ...] = ()
    medical_conditions: tuple[str, ...] = ()
    patient_age: int | None = None
    patient_sex: PatientSex | None = None
    pregnancy_status: PregnancyStatus | None = None
    visit_type: str | None = None
    output_format: DifferentialOutputFormat = DifferentialOutputFormat.JSON

    def __post_init__(self) -> None:
        if not self.chief_complaint.strip():
            raise InvalidClinicalEvidenceError("chief_complaint must not be blank")
        if not self.language.strip():
            raise InvalidClinicalEvidenceError("language must not be blank")
        if self.patient_age is not None and not (0 <= self.patient_age <= _MAX_PLAUSIBLE_AGE):
            raise InvalidClinicalEvidenceError(
                f"patient_age must be between 0 and {_MAX_PLAUSIBLE_AGE} when given"
            )


@dataclass(frozen=True, slots=True)
class DifferentialDiagnosisCandidate(ValueObject):
    """One ranked differential diagnosis candidate, per this task's own
    OUTPUT specification: "Disease Name, ICD-10 Code (optional), Probability/
    Confidence Score, Clinical Reasoning, Supporting Findings, Findings
    Against Diagnosis, Recommended Next Tests, Red Flag Indicators,
    Urgency Level".

    `confidence_score` is nullable — a missing or unparseable confidence
    value from the AI's response is not a parse failure, it is a
    **validation** failure per this task's own "invalid confidence
    scores" category
    (`infrastructure/validation/differential_diagnosis_validator.py`
    raises `InvalidConfidenceScoreError` for `None` or out-of-[0.0, 1.0]
    values) — the same "missing becomes a placeholder value at parse
    time; the validator is what actually rejects it" split
    `app.modules.icd10_ai.domain.value_objects.ICD10Suggestion` documents
    for its own `confidence_score`.
    """

    disease_name: str
    icd10_code: str | None
    confidence_score: float | None
    clinical_reasoning: str
    supporting_findings: tuple[str, ...]
    findings_against: tuple[str, ...]
    recommended_next_tests: tuple[str, ...]
    red_flag_indicators: tuple[str, ...]
    urgency_level: UrgencyLevel


@dataclass(frozen=True, slots=True)
class DifferentialDiagnosisResult(ValueObject):
    """The canonical, structured generation result — always populated
    regardless of `output_format` (a rendering-time concern, per
    `application/services/differential_diagnosis_renderer.py`'s own
    docstring), the same "generation produces structure; rendering
    produces presentation" split
    `app.modules.prescription_ai.domain.value_objects
    .PrescriptionSuggestionSet` establishes for itself.

    `most_likely_diagnosis` is deliberately **not** a separately AI-
    reported field prone to drifting out of sync with `candidates` —
    this task's own "Most Likely Diagnosis" output requirement is instead
    always the top of `candidates` once ranked
    (`application/services/differential_diagnosis_ranking_service.py`),
    so the two can never disagree.
    """

    candidates: tuple[DifferentialDiagnosisCandidate, ...]
    serious_diagnoses_not_to_miss: tuple[str, ...]
    suggested_investigations: tuple[str, ...]
    suggested_referrals: tuple[str, ...]
    raw_text: str
    output_format: DifferentialOutputFormat

    @property
    def is_empty(self) -> bool:
        return len(self.candidates) == 0

    @property
    def most_likely_diagnosis(self) -> str | None:
        return self.candidates[0].disease_name if self.candidates else None


@dataclass(frozen=True, slots=True)
class DifferentialDiagnosisTemplateSet(ValueObject):
    """The three AI-Foundation-registered prompt template names (system/
    developer/user) and pinned version
    `DifferentialDiagnosisTemplateSelectorPort.select` resolves a
    `ClinicalSetting` to — see
    `infrastructure/prompts/template_selector.py`."""

    system_template_name: str
    developer_template_name: str
    user_template_name: str
    version: int


@dataclass(frozen=True, slots=True)
class GenerationSession(ValueObject):
    """The tracked record of one generation attempt, per this task's own
    "AUDIT — Record provider, model, latency, token usage, generation
    status" requirement. `provider`/`model` are plain `str`, not AI
    Foundation's own `AIProviderType`/`AIModel` — this module's domain
    does not import even AI Foundation's *public* types (see this
    module's own docstring)."""

    generation_id: UUID
    provider: str
    model: str
    clinical_setting: str
    language: str
    status: GenerationStatus
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class DifferentialDiagnosisStreamChunk(ValueObject):
    """One increment of a streamed generation — see
    `infrastructure/generation/differential_diagnosis_generator.py`'s own
    docstring for why this is a post-hoc chunking of one complete AI
    Foundation call rather than true token-level streaming."""

    delta: str
    is_final: bool = False
