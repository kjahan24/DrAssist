"""`FollowDoctorService` — "Follow/Unfollow Doctor/Author" (this task's
own FEATURES list). See `DoctorFollower`'s own docstring for why
`followed_user_id` resolves against `UserQueryPort` (`app.modules
.authentication`), not a `doctors.id`-specific port: not every
followable content author is a registered `Doctor` row.

Enforces "Users cannot follow themselves" (this task's own DOMAIN RULES)
*before* any cross-module lookup, since it is a pure input-shape check
needing no I/O — mirrored by a database-level `CHECK` constraint as a
concurrency safety net, see the migration's own docstring. Existence +
tenant match against the followed user are both required
(`UserNotFoundForFollowError` for either — same "cross-tenant existence
is indistinguishable from not-found" reasoning `_target_resolution.py`
establishes for engagement targets).

Idempotent: following a user you already follow is a silent no-op.
"""

from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.community_engagement.application.dto import (
    FollowDoctorInput,
    FollowerSummaryDTO,
)
from app.modules.community_engagement.application.services._summary_mappers import (
    doctor_follower_to_summary,
)
from app.modules.community_engagement.domain.entities import DoctorFollower
from app.modules.community_engagement.domain.exceptions import (
    CannotFollowSelfError,
    UserNotFoundForFollowError,
)
from app.modules.community_engagement.domain.repositories import DoctorFollowerRepository
from app.shared.application.unit_of_work import UnitOfWork


class FollowDoctorService:
    def __init__(
        self,
        *,
        doctor_follower_repository: DoctorFollowerRepository,
        user_query_port: UserQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._followers = doctor_follower_repository
        self._users = user_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: FollowDoctorInput) -> FollowerSummaryDTO:
        if input_dto.follower_user_id == input_dto.followed_user_id:
            raise CannotFollowSelfError(input_dto.follower_user_id)

        followed = await self._users.get_user_summary(input_dto.followed_user_id)
        if followed is None or followed.organization_id != input_dto.organization_id:
            raise UserNotFoundForFollowError(input_dto.followed_user_id)

        existing = await self._followers.get_follow(
            input_dto.follower_user_id, input_dto.followed_user_id
        )
        if existing is not None:
            return doctor_follower_to_summary(existing)

        follower = DoctorFollower.create(
            follower_user_id=input_dto.follower_user_id,
            organization_id=input_dto.organization_id,
            followed_user_id=input_dto.followed_user_id,
        )
        await self._followers.add(follower)
        self._uow.collect_events(follower.pull_events())
        await self._uow.commit()
        return doctor_follower_to_summary(follower)
