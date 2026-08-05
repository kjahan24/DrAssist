"""`ManageCommunityRulesService` — create/update/enable/disable/reorder/
delete a community's own rules. Requires the acting user to hold at
least `ADMIN` role, the same bar `UpdateCommunityService` already sets
for community-level settings changes.

`reorder` is the one method here that touches multiple `CommunityRule`
aggregates in a single call — its own `CommunityRulesReordered` event is
constructed directly and handed to the `UnitOfWork`, rather than routed
through any single aggregate's own `record_event`/`pull_events()` (which
models one aggregate's own history, not a cross-aggregate bulk action).
"""

from uuid import UUID

from app.modules.community.application.dto import (
    CommunityRuleSummaryDTO,
    CreateCommunityRuleInput,
    CreateCommunityRuleOutput,
    DeleteCommunityRuleInput,
    ReorderCommunityRulesInput,
    SetCommunityRuleEnabledInput,
    UpdateCommunityRuleInput,
)
from app.modules.community.application.services._authorization import ensure_role_at_least
from app.modules.community.application.services._summary_mappers import rule_to_summary
from app.modules.community.domain.entities import CommunityRule
from app.modules.community.domain.enums import CommunityRole
from app.modules.community.domain.events import CommunityRulesReordered
from app.modules.community.domain.exceptions import CommunityRuleNotFoundError
from app.modules.community.domain.repositories import (
    CommunityMemberRepository,
    CommunityRuleRepository,
)
from app.modules.community.domain.value_objects import CommunityId, CommunityRuleTitle
from app.shared.application.unit_of_work import UnitOfWork


class ManageCommunityRulesService:
    def __init__(
        self,
        *,
        community_rule_repository: CommunityRuleRepository,
        community_member_repository: CommunityMemberRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._rules = community_rule_repository
        self._members = community_member_repository
        self._uow = unit_of_work

    async def _ensure_admin(self, community_id: UUID, acting_user_id: UUID) -> None:
        member = await self._members.get_by_community_and_user(community_id, acting_user_id)
        ensure_role_at_least(
            member, CommunityRole.ADMIN, community_id=community_id, user_id=acting_user_id
        )

    async def create_rule(self, input_dto: CreateCommunityRuleInput) -> CreateCommunityRuleOutput:
        await self._ensure_admin(input_dto.community_id, input_dto.acting_user_id)

        existing = await self._rules.list_by_community(input_dto.community_id)
        next_position = len(existing)

        rule = CommunityRule.create(
            community_id=CommunityId(input_dto.community_id),
            title=CommunityRuleTitle(input_dto.title),
            description=input_dto.description,
            position=next_position,
        )
        await self._rules.add(rule)
        self._uow.collect_events(rule.pull_events())
        await self._uow.commit()

        return CreateCommunityRuleOutput(
            rule_id=rule.id,
            community_id=input_dto.community_id,
            title=str(rule.title),
            position=rule.position,
        )

    async def update_rule(self, input_dto: UpdateCommunityRuleInput) -> None:
        await self._ensure_admin(input_dto.community_id, input_dto.acting_user_id)

        rule = await self._rules.get_by_id(input_dto.rule_id)
        if rule is None or rule.community_id.value != input_dto.community_id:
            raise CommunityRuleNotFoundError(input_dto.rule_id)

        title = CommunityRuleTitle(input_dto.title) if input_dto.title is not None else None
        rule.update_details(title=title, description=input_dto.description)

        await self._rules.add(rule)
        self._uow.collect_events(rule.pull_events())
        await self._uow.commit()

    async def set_enabled(self, input_dto: SetCommunityRuleEnabledInput) -> None:
        await self._ensure_admin(input_dto.community_id, input_dto.acting_user_id)

        rule = await self._rules.get_by_id(input_dto.rule_id)
        if rule is None or rule.community_id.value != input_dto.community_id:
            raise CommunityRuleNotFoundError(input_dto.rule_id)

        rule.set_enabled(input_dto.enabled)

        await self._rules.add(rule)
        self._uow.collect_events(rule.pull_events())
        await self._uow.commit()

    async def delete_rule(self, input_dto: DeleteCommunityRuleInput) -> None:
        await self._ensure_admin(input_dto.community_id, input_dto.acting_user_id)

        rule = await self._rules.get_by_id(input_dto.rule_id)
        if rule is None or rule.community_id.value != input_dto.community_id:
            raise CommunityRuleNotFoundError(input_dto.rule_id)

        await self._rules.remove(input_dto.rule_id)
        await self._uow.commit()

    async def reorder(self, input_dto: ReorderCommunityRulesInput) -> None:
        await self._ensure_admin(input_dto.community_id, input_dto.acting_user_id)

        rules_by_id = {
            rule.id: rule for rule in await self._rules.list_by_community(input_dto.community_id)
        }
        for position, rule_id in enumerate(input_dto.ordered_rule_ids):
            rule = rules_by_id.get(rule_id)
            if rule is None:
                raise CommunityRuleNotFoundError(rule_id)
            rule.reposition(position)
            await self._rules.add(rule)

        self._uow.collect_events(
            [
                CommunityRulesReordered(
                    community_id=input_dto.community_id,
                    rule_ids=tuple(input_dto.ordered_rule_ids),
                )
            ]
        )
        await self._uow.commit()

    async def list_rules(
        self, community_id: UUID, *, include_disabled: bool = True
    ) -> list[CommunityRuleSummaryDTO]:
        rules = await self._rules.list_by_community(community_id, include_disabled=include_disabled)
        return [rule_to_summary(rule) for rule in rules]
