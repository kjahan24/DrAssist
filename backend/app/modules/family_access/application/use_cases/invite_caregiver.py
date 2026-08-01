"""`InviteCaregiver` — a patient (or staff acting for them) invites an
existing `User` to become a caregiver with a given `Relationship`/
`AccessLevel`.

`organization_id` is derived from the patient's own summary (never
accepted as a separate, independently trustable input) — the same
cross-module dependency pattern every prior module's own "create"
use case already establishes. The caregiver is resolved through
`UserQueryPort` (the Authentication module's public port); a caregiver
`User` belonging to a *different* organization than the patient is
treated identically to a missing one — `CaregiverNotFoundError`, never a
distinct "wrong organization" error — the same cross-tenant-as-not-found
pattern `app.modules.appointment.application.use_cases
.create_appointment.CreateAppointment` already establishes for its own
`doctor_id` check.

The raw invitation token is generated here (never in the domain layer,
which performs no I/O — `secrets.token_urlsafe` is non-deterministic)
and hashed before being handed to `FamilyAccess.create()`; the raw value
is returned in `InviteCaregiverOutput` and nowhere else — see
`domain/entities.py`'s own module docstring. `get_by_invitation_token`
is checked defensively before persisting, mirroring
`app.modules.documents.application.use_cases.upload_medical_document
.UploadMedicalDocument`'s own defensive `stored_filename` collision
check, even though a 256-bit token collision is astronomically
unlikely.
"""

from datetime import UTC, datetime, timedelta

from app.core.security.invitation_token_hashing import (
    generate_raw_invitation_token,
    hash_invitation_token,
)
from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.family_access.application.constants import INVITATION_EXPIRY_DAYS
from app.modules.family_access.application.dto import (
    InviteCaregiverInput,
    InviteCaregiverOutput,
)
from app.modules.family_access.domain.entities import FamilyAccess
from app.modules.family_access.domain.exceptions import (
    CaregiverNotFoundError,
    DuplicateActiveAccessError,
    DuplicateInvitationTokenError,
    PatientNotFoundError,
)
from app.modules.family_access.domain.repositories import FamilyAccessRepository
from app.modules.family_access.domain.value_objects import InvitationTokenHash
from app.modules.patient.public.interfaces import PatientQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class InviteCaregiver(UseCase[InviteCaregiverInput, InviteCaregiverOutput]):
    def __init__(
        self,
        *,
        family_access_repository: FamilyAccessRepository,
        patient_query_port: PatientQueryPort,
        user_query_port: UserQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._grants = family_access_repository
        self._patients = patient_query_port
        self._users = user_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: InviteCaregiverInput) -> InviteCaregiverOutput:
        patient_summary = await self._patients.get_patient_summary(input_dto.patient_id)
        if patient_summary is None:
            raise PatientNotFoundError(input_dto.patient_id)
        organization_id = patient_summary.organization_id

        caregiver_summary = await self._users.get_user_summary(input_dto.caregiver_user_id)
        if caregiver_summary is None or caregiver_summary.organization_id != organization_id:
            raise CaregiverNotFoundError(input_dto.caregiver_user_id)

        existing = await self._grants.get_active_by_patient_and_caregiver(
            patient_id=input_dto.patient_id, caregiver_user_id=input_dto.caregiver_user_id
        )
        if existing is not None:
            raise DuplicateActiveAccessError(input_dto.patient_id, input_dto.caregiver_user_id)

        raw_token = generate_raw_invitation_token()
        token_hash = InvitationTokenHash(hash_invitation_token(raw_token))
        if await self._grants.get_by_invitation_token(token_hash) is not None:
            raise DuplicateInvitationTokenError()

        now = datetime.now(UTC)
        invitation_expires_at = now + timedelta(days=INVITATION_EXPIRY_DAYS)

        grant = FamilyAccess.create(
            organization_id=organization_id,
            patient_id=input_dto.patient_id,
            caregiver_user_id=input_dto.caregiver_user_id,
            relationship=input_dto.relationship,
            access_level=input_dto.access_level,
            invitation_token=token_hash,
            invitation_expires_at=invitation_expires_at,
            notes=input_dto.notes,
        )
        await self._grants.add(grant)
        self._uow.collect_events(grant.pull_events())
        await self._uow.commit()

        return InviteCaregiverOutput(
            family_access_id=grant.id,
            organization_id=organization_id,
            patient_id=grant.patient_id,
            caregiver_user_id=grant.caregiver_user_id,
            status=grant.status,
            invitation_token=raw_token,
            invitation_expires_at=grant.invitation_expires_at,
        )
