"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.community.domain.entities import (
    Community,
    CommunityCategory,
    CommunityMember,
    CommunityRule,
    CommunityTag,
)
from app.modules.community.domain.value_objects import (
    CommunityCategoryName,
    CommunityDescription,
    CommunityId,
    CommunityName,
    CommunityRuleTitle,
    CommunitySlug,
    CommunityTagName,
)
from app.modules.community.infrastructure.models import (
    CommunityCategoryModel,
    CommunityMemberModel,
    CommunityModel,
    CommunityRuleModel,
    CommunityTagModel,
)

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
        category_id=model.category_id,
        avatar_storage_path=model.avatar_storage_path,
        banner_storage_path=model.banner_storage_path,
        is_verified=model.is_verified,
        is_featured=model.is_featured,
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
    model.category_id = entity.category_id
    model.avatar_storage_path = entity.avatar_storage_path
    model.banner_storage_path = entity.banner_storage_path
    model.is_verified = entity.is_verified
    model.is_featured = entity.is_featured


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


# --- CommunityCategory ---------------------------------------------------


def community_category_to_domain(model: CommunityCategoryModel) -> CommunityCategory:
    return CommunityCategory(
        id=model.id,
        name=CommunityCategoryName(model.name),
        slug=CommunitySlug(model.slug),
        description=model.description,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_community_category_to_model(
    entity: CommunityCategory, model: CommunityCategoryModel
) -> None:
    model.id = entity.id
    model.name = str(entity.name)
    model.slug = str(entity.slug)
    model.description = entity.description
    model.is_active = entity.is_active


# --- CommunityTag --------------------------------------------------------


def community_tag_to_domain(model: CommunityTagModel) -> CommunityTag:
    return CommunityTag(
        id=model.id,
        name=CommunityTagName(model.name),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_community_tag_to_model(entity: CommunityTag, model: CommunityTagModel) -> None:
    model.id = entity.id
    model.name = str(entity.name)


# --- CommunityRule ---------------------------------------------------------


def community_rule_to_domain(model: CommunityRuleModel) -> CommunityRule:
    return CommunityRule(
        id=model.id,
        community_id=CommunityId(model.community_id),
        title=CommunityRuleTitle(model.title),
        description=model.description,
        position=model.position,
        is_enabled=model.is_enabled,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_community_rule_to_model(entity: CommunityRule, model: CommunityRuleModel) -> None:
    model.id = entity.id
    model.community_id = entity.community_id.value
    model.title = str(entity.title)
    model.description = entity.description
    model.position = entity.position
    model.is_enabled = entity.is_enabled
