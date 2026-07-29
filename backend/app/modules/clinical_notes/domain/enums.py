"""Enums owned by the Clinical Notes module's domain."""

from enum import StrEnum


class ClinicalNoteType(StrEnum):
    INITIAL = "initial"
    FOLLOW_UP = "follow_up"
    EMERGENCY = "emergency"
    CONSULTATION = "consultation"
    DISCHARGE = "discharge"


class ClinicalNoteStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    SIGNED = "signed"
    LOCKED = "locked"
