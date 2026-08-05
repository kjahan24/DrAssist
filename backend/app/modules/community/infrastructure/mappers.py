"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.community.domain.entities import Community, CommunityMember
from app.modules.community.domain.value_objects import (
    CommunityDescription,
    CommunityId,
    CommunityName,
    CommunitySlug,
)
from app.modules.community.infrastructure.models import CommunityMemberModel, CommunityModel

# --- Community ---------------------------------------------------------------


def community_to_domain(model: CommunityModel) -> Community:
    return Community(
        id=model.id,
        organization_id=model.organization_id,
        slug=CommunitySlug(model.slug),
        name=CommunityName(model.name),
        description=CommunityDescription(model.description) if model.description else None,
        visibility=model.visibility,
        created_by=model.created_by,
        updated_by=model.updated_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_community_to_model(entity: Community, model: CommunityModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.slug = str(entity.slug)
    model.name = str(entity.name)
    model.description = str(entity.description) if entity.description is not None else None
    model.visibility = entity.visibility
    model.created_by = entity.created_by
    model.updated_by = entity.updated_by


# --- CommunityMember -----------------------------------------------------


def community_member_to_domain(model: CommunityMemberModel) -> CommunityMember:
    return CommunityMember(
        id=model.id,
        community_id=CommunityId(model.community_id),
        user_id=model.user_id,
        role=model.role,
        status=model.status,
        joined_at=model.joined_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_community_member_to_model(entity: CommunityMember, model: CommunityMemberModel) -> None:
    model.id = entity.id
    model.community_id = entity.community_id.value
    model.user_id = entity.user_id
    model.role = entity.role
    model.status = entity.status
    model.joined_at = entity.joined_at
