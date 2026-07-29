"""Enums owned by the Chief Complaints module's domain."""

from enum import StrEnum


class DurationUnit(StrEnum):
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"


class Severity(StrEnum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class Onset(StrEnum):
    SUDDEN = "sudden"
    GRADUAL = "gradual"
