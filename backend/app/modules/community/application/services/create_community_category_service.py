"""`CreateCommunityCategoryService` — the actual "extensibility" code
path for `CommunityCategory` (see that entity's own docstring for why
categories are a real table rather than a closed `StrEnum`). Not named
in this task's own APPLICATION list, but required to make "Categories
must be extensible" true rather than aspirational — a system with no way
to add a category isn't extensible, so this is added the same way
`DeleteCommunityService` was added in Phase 5.1 to satisfy an explicit
requirement its own use-case list otherwise omitted.

No community-role check here — categories are platform-wide, not
scoped to one community, so there is no single community whose
`CommunityRole` could gate this. Left open (any authenticated caller)
at this foundation stage, matching how `POST /organizations` is the one
endpoint with no owning-tenant role check yet, for the analogous reason
("no existing scope to check a role against"); a future admin-console
module can add a platform-level permission gate without this service
needing to change.
"""

from app.modules.community.application.dto import (
    CreateCommunityCategoryInput,
    CreateCommunityCategoryOutput,
)
from app.modules.community.domain.entities import CommunityCategory
from app.modules.community.domain.exceptions import DuplicateCommunityCategoryNameError
from app.modules.community.domain.repositories import CommunityCategoryRepository
from app.modules.community.domain.value_objects import CommunityCategoryName, CommunitySlug
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreateCommunityCategoryService(
    UseCase[CreateCommunityCategoryInput, CreateCommunityCategoryOutput]
):
    def __init__(
        self,
        *,
        community_category_repository: CommunityCategoryRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._categories = community_category_repository
        self._uow = unit_of_work

    async def execute(
        self, input_dto: CreateCommunityCategoryInput
    ) -> CreateCommunityCategoryOutput:
        name = CommunityCategoryName(input_dto.name)
        slug = CommunitySlug(input_dto.slug)

        existing = await self._categories.get_by_name(str(name))
        if existing is not None:
            raise DuplicateCommunityCategoryNameError(str(name))

        category = CommunityCategory.create(name=name, slug=slug, description=input_dto.description)
        await self._categories.add(category)
        self._uow.collect_events(category.pull_events())
        await self._uow.commit()

        return CreateCommunityCategoryOutput(
            category_id=category.id, name=str(category.name), slug=str(category.slug)
        )
