"""Domain value objects for the Community Moderation module.

`UserModerationStatus` is deliberately a plain, unpersisted value object —
not a stored aggregate with its own table/repository. A user's "current
moderation status" is a computed reduction over their currently-active
`ModerationRestriction` rows (see `entities.py`'s own module docstring),
not state that is itself ever directly created or mutated — storing it
separately would be exactly the kind of denormalized, driftable counter
this task's own "All counters must remain consistent" precedent (and
`app.modules.community_engagement`'s identical "counts computed live,
never denormalized" choice for vote counts) already established a
precedent for avoiding. `GetModerationStatusService` builds one of these
on every call from a fresh `ModerationRestrictionRepository` query.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.community_moderation.domain.enums import ModerationRestrictionType


@dataclass(frozen=True, slots=True)
class UserModerationStatus:
    user_id: UUID
    community_id: UUID | None
    current_restriction_type: ModerationRestrictionType | None
    restricted_until: datetime | None
    active_restriction_count: int

    @property
    def is_restricted(self) -> bool:
        return self.current_restriction_type is not None
