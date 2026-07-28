"""Enums owned by the Visit module's domain."""

from enum import StrEnum


class VisitType(StrEnum):
    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    EMERGENCY = "emergency"
    TELEMEDICINE = "telemedicine"
    PROCEDURE = "procedure"
    LAB_REVIEW = "lab_review"
    VACCINATION = "vaccination"
    HOME_VISIT = "home_visit"


class VisitStatus(StrEnum):
    SCHEDULED = "scheduled"
    CHECKED_IN = "checked_in"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class VisitPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"
