"""The Family / Caregiver Access module's public port — the only
contract another module may depend on. See
`docs/backend-architecture/03_module_architecture.md` and
`10_module_communication.md`.

Never import from `app.modules.family_access.domain`, `.application`
(beyond this package), or `.infrastructure` from outside this module —
this file and `dto.py` are the entire allowed surface today, with one
deliberate exception: `AccessLevel` (a plain enum, not behavior) is
imported directly from `domain.enums`, the same "peer domain enums are
value types, not behavior" allowance every other module's own public
DTOs already rely on (e.g. `MedicalDocumentSummaryDTO.category` uses
`app.modules.documents.domain.enums.DocumentCategory` the same way).

`get_active_access_level` is the integration point future modules
(Patient Portal, Personal Health Dashboard, Personal Health Timeline,
Medical Community, Emergency Access, ...) are expected to depend on to
answer "does this caregiver currently have access to this patient, and
at what level" — see `container.py`'s own scope note for why
authorization *enforcement* is deliberately not built here.
`get_invitation_by_token`/`list_pending_invitations` are **not** exposed
on this port: no other module needs to resolve a raw invitation token or
list a caregiver's pending invites — those stay internal to this
module's own `api/router.py`.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.family_access.domain.enums import AccessLevel
from app.modules.family_access.public.dto import FamilyAccessSummaryDTO


class FamilyAccessQueryPort(ABC):
    @abstractmethod
    async def family_access_exists(self, family_access_id: UUID) -> bool: ...

    @abstractmethod
    async def get_family_access_summary(
        self, family_access_id: UUID
    ) -> FamilyAccessSummaryDTO | None: ...

    @abstractmethod
    async def get_patient_caregivers(self, patient_id: UUID) -> list[FamilyAccessSummaryDTO]: ...

    @abstractmethod
    async def get_caregiver_patients(
        self, caregiver_user_id: UUID
    ) -> list[FamilyAccessSummaryDTO]: ...

    @abstractmethod
    async def get_active_access_level(
        self, *, patient_id: UUID, caregiver_user_id: UUID
    ) -> AccessLevel | None: ...
