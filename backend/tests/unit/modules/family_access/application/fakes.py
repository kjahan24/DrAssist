"""In-memory test doubles for the Family / Caregiver Access module's
repository, Unit of Work, and the Patient/Authentication modules'
cross-module ports the use cases depend on — each implements the exact
same interface its real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database or another module's facade.
"""

from datetime import date
from uuid import UUID, uuid4

from app.modules.authentication.domain.enums import UserStatus
from app.modules.authentication.public.dto import UserSummaryDTO
from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.family_access.domain.entities import FamilyAccess
from app.modules.family_access.domain.enums import FamilyAccessStatus
from app.modules.family_access.domain.repositories import FamilyAccessRepository
from app.modules.family_access.domain.value_objects import InvitationTokenHash
from app.modules.patient.domain.enums import Gender, PatientStatus
from app.modules.patient.public.dto import (
    PatientAllergySummaryDTO,
    PatientMedicalConditionSummaryDTO,
    PatientSummaryDTO,
)
from app.modules.patient.public.interfaces import PatientQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent

_ACTIVE_STATUSES = (FamilyAccessStatus.PENDING, FamilyAccessStatus.ACCEPTED)


class FakeFamilyAccessRepository(FamilyAccessRepository):
    def __init__(self) -> None:
        self._grants: dict[UUID, FamilyAccess] = {}

    async def get_by_id(self, family_access_id: UUID) -> FamilyAccess | None:
        return self._grants.get(family_access_id)

    async def get_by_invitation_token(
        self, invitation_token: InvitationTokenHash
    ) -> FamilyAccess | None:
        for grant in self._grants.values():
            if grant.invitation_token == invitation_token:
                return grant
        return None

    async def get_active_by_patient_and_caregiver(
        self, *, patient_id: UUID, caregiver_user_id: UUID
    ) -> FamilyAccess | None:
        for grant in self._grants.values():
            if (
                grant.patient_id == patient_id
                and grant.caregiver_user_id == caregiver_user_id
                and grant.status in _ACTIVE_STATUSES
            ):
                return grant
        return None

    async def list_by_patient(self, patient_id: UUID) -> list[FamilyAccess]:
        matches = [g for g in self._grants.values() if g.patient_id == patient_id]
        return sorted(matches, key=lambda g: g.created_at, reverse=True)

    async def list_by_caregiver(self, caregiver_user_id: UUID) -> list[FamilyAccess]:
        matches = [g for g in self._grants.values() if g.caregiver_user_id == caregiver_user_id]
        return sorted(matches, key=lambda g: g.created_at, reverse=True)

    async def list_pending_by_caregiver(self, caregiver_user_id: UUID) -> list[FamilyAccess]:
        matches = [
            g
            for g in self._grants.values()
            if g.caregiver_user_id == caregiver_user_id and g.status is FamilyAccessStatus.PENDING
        ]
        return sorted(matches, key=lambda g: g.created_at, reverse=True)

    async def add(self, family_access: FamilyAccess) -> None:
        self._grants[family_access.id] = family_access


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.published_events: list[DomainEvent] = []
        self._pending_events: list[DomainEvent] = []

    def collect_events(self, events: list[DomainEvent]) -> None:
        self._pending_events.extend(events)

    async def commit(self) -> None:
        self.committed = True
        self.published_events.extend(self._pending_events)
        self._pending_events = []

    async def rollback(self) -> None:
        self.rolled_back = True
        self._pending_events = []

    async def flush(self) -> None:
        pass


class FakePatientQueryPort(PatientQueryPort):
    """Backed by a settable map of "existing" patient id -> organization
    id — `InviteCaregiver` calls `get_patient_summary` both to check
    existence and to derive `organization_id`."""

    def __init__(self, *, existing_patients: dict[UUID, UUID] | None = None) -> None:
        self.existing_patients = existing_patients or {}

    async def patient_exists(self, patient_id: UUID) -> bool:
        return patient_id in self.existing_patients

    async def is_active(self, patient_id: UUID) -> bool:
        return patient_id in self.existing_patients

    async def get_patient_summary(self, patient_id: UUID) -> PatientSummaryDTO | None:
        organization_id = self.existing_patients.get(patient_id)
        if organization_id is None:
            return None
        return PatientSummaryDTO(
            patient_id=patient_id,
            organization_id=organization_id,
            patient_number="PAT-0001",
            first_name="Jane",
            last_name="Doe",
            gender=Gender.FEMALE,
            date_of_birth=date(1990, 1, 1),
            status=PatientStatus.ACTIVE,
        )

    async def list_allergies_for_patient(self, patient_id: UUID) -> list[PatientAllergySummaryDTO]:
        return []

    async def list_medical_conditions_for_patient(
        self, patient_id: UUID
    ) -> list[PatientMedicalConditionSummaryDTO]:
        return []


class FakeUserQueryPort(UserQueryPort):
    """Backed by a settable map of "existing" user id -> organization id
    — `InviteCaregiver` calls `get_user_summary` both to check existence
    and to confirm the caregiver belongs to the same organization as the
    patient."""

    def __init__(self, *, existing_users: dict[UUID, UUID] | None = None) -> None:
        self.existing_users = existing_users or {}

    async def user_exists(self, user_id: UUID) -> bool:
        return user_id in self.existing_users

    async def get_user_summary(self, user_id: UUID) -> UserSummaryDTO | None:
        organization_id = self.existing_users.get(user_id)
        if organization_id is None:
            return None
        return UserSummaryDTO(
            user_id=user_id,
            organization_id=organization_id,
            email=f"caregiver-{uuid4().hex[:8]}@example.com",
            first_name="Cara",
            last_name="Giver",
            status=UserStatus.ACTIVE,
        )
