"""Enums owned by the ICD-10 Coding module's domain."""

from enum import StrEnum


class CodingSource(StrEnum):
    PHYSICIAN = "physician"
    AI = "ai"
    HYBRID = "hybrid"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
