"""Enums owned by the Diagnosis module's domain."""

from enum import StrEnum


class DiagnosisType(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    DIFFERENTIAL = "differential"


class DiagnosisStatus(StrEnum):
    PROVISIONAL = "provisional"
    CONFIRMED = "confirmed"
    RULED_OUT = "ruled_out"
