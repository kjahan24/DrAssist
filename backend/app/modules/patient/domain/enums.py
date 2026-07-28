"""Enums owned by the Patient module's domain.

`Gender` intentionally duplicates the Doctor module's enum of the same
name rather than importing it: each module's domain enums are private to
that module's bounded context (see `app.modules.doctor.domain.enums`'s
own `Gender`) — importing across `domain/` packages is exactly what the
`public/` facade boundary exists to prevent. Two same-shaped-but-distinct
`Gender` types is the correct outcome, not duplication of a shared
utility.
"""

from enum import StrEnum


class PatientStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DECEASED = "deceased"


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class BloodGroup(StrEnum):
    A_POSITIVE = "a+"
    A_NEGATIVE = "a-"
    B_POSITIVE = "b+"
    B_NEGATIVE = "b-"
    AB_POSITIVE = "ab+"
    AB_NEGATIVE = "ab-"
    O_POSITIVE = "o+"
    O_NEGATIVE = "o-"


class MaritalStatus(StrEnum):
    SINGLE = "single"
    MARRIED = "married"
    DIVORCED = "divorced"
    WIDOWED = "widowed"
    SEPARATED = "separated"


class ContactType(StrEnum):
    MOBILE = "mobile"
    HOME = "home"
    OFFICE = "office"
    OTHER = "other"


class InsuranceStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"


class AllergyType(StrEnum):
    DRUG = "drug"
    FOOD = "food"
    ENVIRONMENTAL = "environmental"
    INSECT = "insect"
    LATEX = "latex"
    OTHER = "other"


class AllergySeverity(StrEnum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    LIFE_THREATENING = "life_threatening"


class AllergyStatus(StrEnum):
    ACTIVE = "active"
    RESOLVED = "resolved"


class RouteOfAdministration(StrEnum):
    ORAL = "oral"
    IV = "iv"
    IM = "im"
    SC = "sc"
    TOPICAL = "topical"
    INHALATION = "inhalation"
    OTHER = "other"


class AdherenceStatus(StrEnum):
    TAKING = "taking"
    STOPPED = "stopped"
    COMPLETED = "completed"
    UNKNOWN = "unknown"


class ConditionSeverity(StrEnum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class ConditionStatus(StrEnum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    CHRONIC = "chronic"
    IN_REMISSION = "in_remission"
