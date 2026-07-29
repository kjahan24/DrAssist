"""Enums owned by the Lab Results module's domain."""

from enum import StrEnum


class LabResultStatus(StrEnum):
    DRAFT = "draft"
    FINAL = "final"


class AbnormalFlag(StrEnum):
    NORMAL = "normal"
    LOW = "low"
    HIGH = "high"
    CRITICAL = "critical"
    ABNORMAL = "abnormal"
