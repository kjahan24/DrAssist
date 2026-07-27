"""Domain events published by Organization module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class OrganizationCreated(DomainEvent):
    organization_id: UUID
    organization_code: str
    name: str


@dataclass(frozen=True, kw_only=True)
class OrganizationProfileUpdated(DomainEvent):
    organization_id: UUID


@dataclass(frozen=True, kw_only=True)
class OrganizationActivated(DomainEvent):
    organization_id: UUID


@dataclass(frozen=True, kw_only=True)
class OrganizationDeactivated(DomainEvent):
    organization_id: UUID


@dataclass(frozen=True, kw_only=True)
class OrganizationSettingsCreated(DomainEvent):
    organization_id: UUID
    settings_id: UUID


@dataclass(frozen=True, kw_only=True)
class OrganizationSettingsUpdated(DomainEvent):
    organization_id: UUID
    settings_id: UUID


@dataclass(frozen=True, kw_only=True)
class DepartmentCreated(DomainEvent):
    department_id: UUID
    organization_id: UUID
    name: str


@dataclass(frozen=True, kw_only=True)
class DepartmentUpdated(DomainEvent):
    department_id: UUID
    organization_id: UUID


@dataclass(frozen=True, kw_only=True)
class DepartmentStatusChanged(DomainEvent):
    department_id: UUID
    organization_id: UUID
    status: str
