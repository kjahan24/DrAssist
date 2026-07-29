"""Enums owned by the Clinical Reasoning module's domain."""

from enum import StrEnum


class ReasoningSource(StrEnum):
    PHYSICIAN = "physician"
    AI = "ai"
    HYBRID = "hybrid"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
