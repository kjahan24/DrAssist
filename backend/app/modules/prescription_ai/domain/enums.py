"""Enums owned by the AI Prescription Assistance module's domain."""

from enum import StrEnum


class PrescribingSetting(StrEnum):
    """Drives prompt selection (`infrastructure/prompts/
    template_selector.py`) — each setting has its own independently-
    versioned prompt template set, the same "Support outpatient/
    emergency/inpatient/..." shape
    `app.modules.icd10_ai.domain.enums.CodingSetting` establishes for its
    own module (a distinct member set, not shared — prescribing context
    is not a coding context)."""

    OUTPATIENT = "outpatient"
    EMERGENCY = "emergency"
    INPATIENT = "inpatient"
    PEDIATRIC = "pediatric"
    GERIATRIC = "geriatric"
    FOLLOW_UP = "follow_up"


class PrescriptionOutputFormat(StrEnum):
    """What shape a suggestion set is rendered into. A same-shaped local
    copy of `app.modules.icd10_ai.domain.enums.ICD10OutputFormat` —
    domain code never imports across module boundaries (see
    `domain/value_objects.py`'s own module docstring)."""

    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"


class AdministrationRoute(StrEnum):
    """A same-shaped local copy of
    `app.modules.prescriptions.domain.enums.AdministrationRoute` — this
    module's domain never imports a peer module's domain enum, but the
    real-world route vocabulary a prescription draft needs is identical,
    so it is worth mirroring as a closed enum (rather than a free-text
    `str`) the same way that pre-existing, completed module already
    treats it. `OTHER` is what the parser defaults to when the AI's
    returned route text does not match a recognized member — see
    `infrastructure/parsing/prescription_suggestion_parser.py`."""

    ORAL = "oral"
    IV = "iv"
    IM = "im"
    SC = "sc"
    TOPICAL = "topical"
    INHALATION = "inhalation"
    OPHTHALMIC = "ophthalmic"
    OTIC = "otic"
    NASAL = "nasal"
    RECTAL = "rectal"
    VAGINAL = "vaginal"
    OTHER = "other"


class SafetyFindingCategory(StrEnum):
    """The nine categories this task's own "MEDICATION SAFETY" section
    requires AI validation for. Each `MedicationSafetyFinding` is tagged
    with exactly one of these — see that value object's own docstring for
    how AI-reported and deterministically-computed findings (via
    `DrugInteractionPort`/`MedicationKnowledgePort`) are merged."""

    ALLERGY_CONFLICT = "allergy_conflict"
    DUPLICATE_THERAPY = "duplicate_therapy"
    CONTRAINDICATION = "contraindication"
    DRUG_INTERACTION = "drug_interaction"
    PREGNANCY_RISK = "pregnancy_risk"
    PEDIATRIC_DOSING = "pediatric_dosing"
    GERIATRIC_PRECAUTION = "geriatric_precaution"
    RENAL_PRECAUTION = "renal_precaution"
    HEPATIC_PRECAUTION = "hepatic_precaution"


class SafetySeverity(StrEnum):
    """Not explicitly named by this task, but a minimal, closed
    vocabulary a "warning" needs to be clinically actionable at all — the
    same "small, closed vocabulary earns its own enum" reasoning
    `PatientSex`/`DiagnosisFlag` already establish elsewhere in this
    codebase's AI modules."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class GenerationStatus(StrEnum):
    """Recorded on `GenerationSession` for the "generation status" audit
    field this task asks for."""

    COMPLETED = "completed"
    FAILED = "failed"


class PatientSex(StrEnum):
    """A closed, small vocabulary (unlike free-text `language`), worth an
    enum the same way `app.modules.icd10_ai.domain.enums.PatientSex` is
    for its own module — a same-*shaped*, not shared, local copy, since
    domain code never imports a peer module's domain enum."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNSPECIFIED = "unspecified"


class PregnancyStatus(StrEnum):
    """A closed vocabulary for this task's own "Pregnancy Status" input
    field — directly relevant to the "pregnancy risks" medication-safety
    category. `NOT_APPLICABLE` covers patients for whom pregnancy status
    is not a clinically meaningful question (matching `PatientSex.MALE`)
    without forcing a caller to fabricate `NOT_PREGNANT`."""

    NOT_PREGNANT = "not_pregnant"
    PREGNANT = "pregnant"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
