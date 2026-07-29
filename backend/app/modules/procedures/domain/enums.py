"""Enums owned by the Procedures module's domain."""

from enum import StrEnum


class ProcedureStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
