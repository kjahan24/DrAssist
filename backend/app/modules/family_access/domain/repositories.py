"""Repository interface for the `FamilyAccess` aggregate, expressed in
domain vocabulary only (no session, no SQL). Concrete implementation lives
in `app.modules.family_access.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method: a repository returns the actual aggregate object,
the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.family_access.domain.entities import FamilyAccess
from app.modules.family_access.domain.value_objects import InvitationTokenHash


class FamilyAccessRepository(ABC):
    @abstractmethod
    async def get_by_id(self, family_access_id: UUID) -> FamilyAccess | None: ...

    @abstractmethod
    async def get_by_invitation_token(
        self, invitation_token: InvitationTokenHash
    ) -> FamilyAccess | None: ...

    @abstractmethod
    async def get_active_by_patient_and_caregiver(
        self, *, patient_id: UUID, caregiver_user_id: UUID
    ) -> FamilyAccess | None:
        """ "Active" means `Pending` or `Accepted` — the two states the
        "one caregiver cannot have duplicate active access to the same
        patient" business rule cares about; `Rejected`/`Revoked`/
        `Expired` grants never block a new invitation."""
        ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[FamilyAccess]: ...

    @abstractmethod
    async def list_by_caregiver(self, caregiver_user_id: UUID) -> list[FamilyAccess]: ...

    @abstractmethod
    async def list_pending_by_caregiver(self, caregiver_user_id: UUID) -> list[FamilyAccess]: ...

    @abstractmethod
    async def add(self, family_access: FamilyAccess) -> None: ...
