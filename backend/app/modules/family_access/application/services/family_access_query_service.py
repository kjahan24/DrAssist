"""Read-only queries against `FamilyAccess`.

Backs the module's public `FamilyAccessQueryPort` — the one
implementation, per `docs/backend-architecture
/04_repository_and_service_patterns.md`'s service-interface guidance (a
formal interface earns its place at the `public/` boundary; this
internal service doesn't need a second one).

`GetPatientCaregivers`/`GetCaregiverPatients`/`GetInvitation`/
`ListPendingInvitations` (this task's own "Use Cases" list) are plain
read methods here, not `UseCase[Input, Output]` classes — the same
"reads are query-service methods, only mutations get a `UseCase`"
convention every prior module in this codebase already follows (e.g.
`app.modules.documents.application.services.document_query_service
.MedicalDocumentQueryService`).

`get_invitation_by_token` hashes the raw token the same way
`InviteCaregiver` does before looking it up — the caller (a caregiver
who received an invitation link) only ever has the raw value.
`get_active_access_level` exists for future authorization integration
(see `container.py`'s own scope note: "FullMedical allows all patient
record viewing (authorization integration comes later)") — it is the
one method a future module would call to answer "does this caregiver
currently have access to this patient, and at what level", already
built on the same `get_active_by_patient_and_caregiver` repository
method `InviteCaregiver` uses for its own duplicate-access check.
"""

from uuid import UUID

from app.core.security.invitation_token_hashing import hash_invitation_token
from app.modules.family_access.application.dto import FamilyAccessSummaryDTO
from app.modules.family_access.domain.entities import FamilyAccess
from app.modules.family_access.domain.enums import AccessLevel
from app.modules.family_access.domain.repositories import FamilyAccessRepository
from app.modules.family_access.domain.value_objects import InvitationTokenHash


class FamilyAccessQueryService:
    def __init__(self, *, family_access_repository: FamilyAccessRepository) -> None:
        self._grants = family_access_repository

    async def family_access_exists(self, family_access_id: UUID) -> bool:
        return await self._grants.get_by_id(family_access_id) is not None

    async def get_family_access_summary(
        self, family_access_id: UUID
    ) -> FamilyAccessSummaryDTO | None:
        grant = await self._grants.get_by_id(family_access_id)
        return _to_summary(grant) if grant is not None else None

    async def get_patient_caregivers(self, patient_id: UUID) -> list[FamilyAccessSummaryDTO]:
        grants = await self._grants.list_by_patient(patient_id)
        return [_to_summary(grant) for grant in grants]

    async def get_caregiver_patients(self, caregiver_user_id: UUID) -> list[FamilyAccessSummaryDTO]:
        grants = await self._grants.list_by_caregiver(caregiver_user_id)
        return [_to_summary(grant) for grant in grants]

    async def get_invitation_by_token(self, raw_token: str) -> FamilyAccessSummaryDTO | None:
        token_hash = InvitationTokenHash(hash_invitation_token(raw_token))
        grant = await self._grants.get_by_invitation_token(token_hash)
        return _to_summary(grant) if grant is not None else None

    async def list_pending_invitations(
        self, caregiver_user_id: UUID
    ) -> list[FamilyAccessSummaryDTO]:
        grants = await self._grants.list_pending_by_caregiver(caregiver_user_id)
        return [_to_summary(grant) for grant in grants]

    async def get_active_access_level(
        self, *, patient_id: UUID, caregiver_user_id: UUID
    ) -> AccessLevel | None:
        grant = await self._grants.get_active_by_patient_and_caregiver(
            patient_id=patient_id, caregiver_user_id=caregiver_user_id
        )
        return grant.access_level if grant is not None else None


def _to_summary(grant: FamilyAccess) -> FamilyAccessSummaryDTO:
    return FamilyAccessSummaryDTO(
        family_access_id=grant.id,
        organization_id=grant.organization_id,
        patient_id=grant.patient_id,
        caregiver_user_id=grant.caregiver_user_id,
        relationship=grant.relationship,
        access_level=grant.access_level,
        status=grant.status,
        invitation_expires_at=grant.invitation_expires_at,
        accepted_at=grant.accepted_at,
        revoked_at=grant.revoked_at,
        notes=grant.notes,
    )
