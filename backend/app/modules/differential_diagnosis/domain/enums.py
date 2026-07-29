"""Enums owned by the Differential Diagnosis module's domain."""

from enum import StrEnum


class DiagnosisSource(StrEnum):
    PHYSICIAN = "physician"
    AI = "ai"
    HYBRID = "hybrid"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
