"""Domain events published by Family / Caregiver Access module
aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`. Shaped like
`app.modules.notification.domain.events` (`Created`/`StatusChanged` —
one generic status-change event rather than one per transition), the
closest precedent for an aggregate with more than two lifecycle states.
"""

from dataclasses import dataclass
from uuid import UUID

from app.modules.family_access.domain.enums import FamilyAccessStatus
from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class FamilyAccessInvited(DomainEvent):
    family_access_id: UUID
    organization_id: UUID
    patient_id: UUID
    caregiver_user_id: UUID


@dataclass(frozen=True, kw_only=True)
class FamilyAccessStatusChanged(DomainEvent):
    family_access_id: UUID
    old_status: FamilyAccessStatus
    new_status: FamilyAccessStatus
