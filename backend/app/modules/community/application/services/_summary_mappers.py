"""Domain entity -> summary DTO mappers shared by every query-style
service in this package (`community_query_service`,
`browse_communities_service`, `search_communities_service`,
`feature_communities_service`) — kept in one place so there is exactly
one mapping per entity, matching the "exactly one definition of each
shape" precedent every other module's own summary-mapping already
follows for itself.
"""

from app.modules.community.application.dto import (
    CommunityCategorySummaryDTO,
    CommunityMemberSummaryDTO,
    CommunityRuleSummaryDTO,
    CommunitySummaryDTO,
    CommunityTagSummaryDTO,
)
from app.modules.community.domain.entities import (
    Community,
    CommunityCategory,
    CommunityMember,
    CommunityRule,
    CommunityTag,
)


def community_to_summary(community: Community) -> CommunitySummaryDTO:
    return CommunitySummaryDTO(
        community_id=community.id,
        organization_id=community.organization_id,
        slug=str(community.slug),
        name=str(community.name),
        visibility=community.visibility,
        created_at=community.created_at,
        updated_at=community.updated_at,
        description=str(community.description) if community.description is not None else None,
        created_by=community.created_by,
        category_id=community.category_id,
        avatar_storage_path=community.avatar_storage_path,
        banner_storage_path=community.banner_storage_path,
        is_verified=community.is_verified,
        is_featured=community.is_featured,
    )


def member_to_summary(member: CommunityMember) -> CommunityMemberSummaryDTO:
    return CommunityMemberSummaryDTO(
        member_id=member.id,
        community_id=member.community_id.value,
        user_id=member.user_id,
        role=member.role,
        status=member.status,
        joined_at=member.joined_at,
    )


def category_to_summary(category: CommunityCategory) -> CommunityCategorySummaryDTO:
    return CommunityCategorySummaryDTO(
        category_id=category.id,
        name=str(category.name),
        slug=str(category.slug),
        is_active=category.is_active,
        description=category.description,
    )


def tag_to_summary(tag: CommunityTag) -> CommunityTagSummaryDTO:
    return CommunityTagSummaryDTO(tag_id=tag.id, name=str(tag.name))


def rule_to_summary(rule: CommunityRule) -> CommunityRuleSummaryDTO:
    return CommunityRuleSummaryDTO(
        rule_id=rule.id,
        community_id=rule.community_id.value,
        title=str(rule.title),
        position=rule.position,
        is_enabled=rule.is_enabled,
        description=rule.description,
    )
