"""Enums owned by the Prescription module's domain."""

from enum import StrEnum


class PrescriptionStatus(StrEnum):
    DRAFT = "draft"
    FINAL = "final"


class AdministrationRoute(StrEnum):
    ORAL = "oral"
    IV = "iv"
    IM = "im"
    SC = "sc"
    TOPICAL = "topical"
    INHALATION = "inhalation"
    OPHTHALMIC = "ophthalmic"
    OTIC = "otic"
    NASAL = "nasal"
    RECTAL = "rectal"
    VAGINAL = "vaginal"
    OTHER = "other"
