"""Enums owned by the AI Differential Diagnosis module's domain."""

from enum import StrEnum


class ClinicalSetting(StrEnum):
    """Drives prompt selection (`infrastructure/prompts/
    template_selector.py`) — each setting has its own independently-
    versioned prompt template set, the same "Support outpatient/
    emergency/inpatient/..." shape
    `app.modules.prescription_ai.domain.enums.PrescribingSetting`
    establishes for its own module (a distinct member set, not shared —
    this task's own PROMPTS section lists five settings, one fewer than
    `PrescribingSetting`'s six: no "follow-up" setting for differential
    diagnosis)."""

    OUTPATIENT = "outpatient"
    EMERGENCY = "emergency"
    INPATIENT = "inpatient"
    PEDIATRIC = "pediatric"
    GERIATRIC = "geriatric"


class DifferentialOutputFormat(StrEnum):
    """What shape a result is rendered into. A same-shaped local copy of
    `app.modules.prescription_ai.domain.enums.PrescriptionOutputFormat`
    — domain code never imports across module boundaries (see
    `domain/value_objects.py`'s own module docstring)."""

    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"


class UrgencyLevel(StrEnum):
    """The closed triage-style vocabulary this task's own "Urgency
    Level" output field and "urgency classification" clinical-reasoning
    requirement need. Ordered from least to most acute — see
    `infrastructure/reasoning/clinical_reasoning_service.py`'s own
    docstring for how this ordering is used to compute a deterministic
    *minimum* urgency from red-flag indicators."""

    ROUTINE = "routine"
    URGENT = "urgent"
    EMERGENT = "emergent"


class GenerationStatus(StrEnum):
    """Recorded on `GenerationSession` for the "generation status" audit
    field this task asks for."""

    COMPLETED = "completed"
    FAILED = "failed"


class PatientSex(StrEnum):
    """A closed, small vocabulary (unlike free-text `language`), worth an
    enum the same way `app.modules.prescription_ai.domain.enums
    .PatientSex` is for its own module — a same-*shaped*, not shared,
    local copy, since domain code never imports a peer module's domain
    enum."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNSPECIFIED = "unspecified"


class PregnancyStatus(StrEnum):
    """A same-shaped local copy of `app.modules.prescription_ai.domain
    .enums.PregnancyStatus` — pregnancy status is directly relevant to
    differential diagnosis (e.g. ruling in/out pregnancy-related
    diagnoses), the same reasoning that module's own docstring
    documents."""

    NOT_PREGNANT = "not_pregnant"
    PREGNANT = "pregnant"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
