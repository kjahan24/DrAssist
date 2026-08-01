"""Enums owned by the Family / Caregiver Access module's domain."""

from enum import StrEnum


class Relationship(StrEnum):
    PARENT = "parent"
    CHILD = "child"
    SPOUSE = "spouse"
    SIBLING = "sibling"
    GUARDIAN = "guardian"
    CAREGIVER = "caregiver"
    RELATIVE = "relative"
    FRIEND = "friend"
    OTHER = "other"


class AccessLevel(StrEnum):
    READ_ONLY = "read_only"
    LIMITED_MEDICAL = "limited_medical"
    FULL_MEDICAL = "full_medical"


class FamilyAccessStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REVOKED = "revoked"
    EXPIRED = "expired"
