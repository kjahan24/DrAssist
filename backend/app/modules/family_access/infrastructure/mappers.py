"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.family_access.domain.entities import FamilyAccess
from app.modules.family_access.domain.value_objects import InvitationTokenHash
from app.modules.family_access.infrastructure.models import FamilyAccessModel


def family_access_to_domain(model: FamilyAccessModel) -> FamilyAccess:
    return FamilyAccess(
        id=model.id,
        organization_id=model.organization_id,
        patient_id=model.patient_id,
        caregiver_user_id=model.caregiver_user_id,
        relationship=model.relationship,
        access_level=model.access_level,
        invitation_token=InvitationTokenHash(model.invitation_token),
        invitation_expires_at=model.invitation_expires_at,
        status=model.status,
        accepted_at=model.accepted_at,
        revoked_at=model.revoked_at,
        notes=model.notes,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_family_access_to_model(entity: FamilyAccess, model: FamilyAccessModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.patient_id = entity.patient_id
    model.caregiver_user_id = entity.caregiver_user_id
    model.relationship = entity.relationship
    model.access_level = entity.access_level
    model.invitation_token = str(entity.invitation_token)
    model.invitation_expires_at = entity.invitation_expires_at
    model.status = entity.status
    model.accepted_at = entity.accepted_at
    model.revoked_at = entity.revoked_at
    model.notes = entity.notes
