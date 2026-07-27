"""Enums owned by the Organization module's domain."""

from enum import StrEnum


class OrganizationType(StrEnum):
    CLINIC = "clinic"
    HOSPITAL = "hospital"
    DIAGNOSTIC = "diagnostic"
    TELEMEDICINE = "telemedicine"


class DepartmentStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
