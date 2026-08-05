"""Value objects specific to the Community module.

`CommunityId` is a deliberate, disclosed departure from the plain-`UUID`
identity every other module's aggregate uses for cross-aggregate
references (e.g. `Department.organization_id: UUID`) — this task's own
VALUE OBJECTS section explicitly names `CommunityId` alongside
`CommunitySlug`/`CommunityName`/`CommunityDescription`. Rather than fork
`app.shared.domain.entity.Entity.id`'s own `UUID` contract (which every
repository/mapper/session call across the whole codebase depends on, and
which rule 1/2 protect), `Community.id` itself stays a plain `UUID`
exactly like every other aggregate root; `CommunityId` is used only as
the strongly-typed *reference* field on `CommunityMember.community_id` —
the "each aggregate reference to another aggregate is by ID only" field
`docs/backend-architecture/03_module_architecture.md` already calls for,
just given its own type here (instead of a bare `UUID`) so it can never
be swapped by accident with `CommunityMember.user_id` (also a UUID,
referencing a different aggregate entirely).
"""

import re
from dataclasses import dataclass
from uuid import UUID

from app.modules.community.domain.exceptions import (
    CommunityCategoryNameRequiredError,
    CommunityCategoryNameTooLongError,
    CommunityDescriptionRequiredError,
    CommunityDescriptionTooLongError,
    CommunityNameRequiredError,
    CommunityNameTooLongError,
    CommunityRuleTitleRequiredError,
    CommunityRuleTitleTooLongError,
    CommunityTagNameRequiredError,
    CommunityTagNameTooLongError,
    InvalidCommunitySlugError,
)
from app.shared.domain.value_object import ValueObject

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_MIN_LENGTH = 3
_SLUG_MAX_LENGTH = 64
_NAME_MAX_LENGTH = 200
_DESCRIPTION_MAX_LENGTH = 2000
_CATEGORY_NAME_MAX_LENGTH = 100
_TAG_NAME_MAX_LENGTH = 50
_RULE_TITLE_MAX_LENGTH = 200


@dataclass(frozen=True, slots=True)
class CommunityId(ValueObject):
    value: UUID

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class CommunitySlug(ValueObject):
    """A URL-safe, tenant-scoped identifier, e.g. `"diabetes-support"`.
    Normalized to lowercase (trimmed of surrounding whitespace) so lookups
    are case-insensitive without needing a `CITEXT` column — the same
    "normalize once, in the value object, plain `Text` column underneath"
    approach `app.modules.organization.domain.value_objects
    .OrganizationCode` establishes for itself, just lowercase instead of
    uppercase.
    """

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not (_SLUG_MIN_LENGTH <= len(normalized) <= _SLUG_MAX_LENGTH) or not _SLUG_PATTERN.match(
            normalized
        ):
            raise InvalidCommunitySlugError(self.value)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class CommunityName(ValueObject):
    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise CommunityNameRequiredError()
        if len(stripped) > _NAME_MAX_LENGTH:
            raise CommunityNameTooLongError(_NAME_MAX_LENGTH)
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class CommunityDescription(ValueObject):
    """Optional free text — `Community.description` is `CommunityDescription
    | None`, never an empty-string `CommunityDescription`; a caller with
    nothing to say passes `None`, not a blank description (the same
    "missing is `None`, not an empty value object" rule every optional
    field in this codebase follows).
    """

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise CommunityDescriptionRequiredError()
        if len(stripped) > _DESCRIPTION_MAX_LENGTH:
            raise CommunityDescriptionTooLongError(_DESCRIPTION_MAX_LENGTH)
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class CommunityCategoryName(ValueObject):
    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise CommunityCategoryNameRequiredError()
        if len(stripped) > _CATEGORY_NAME_MAX_LENGTH:
            raise CommunityCategoryNameTooLongError(_CATEGORY_NAME_MAX_LENGTH)
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class CommunityTagName(ValueObject):
    """Normalized to lowercase so tags are reusable/deduplicated
    case-insensitively — `"Diabetes"` and `"diabetes"` resolve to the
    same tag, the same normalize-in-the-value-object approach
    `CommunitySlug` already establishes for itself."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not normalized:
            raise CommunityTagNameRequiredError()
        if len(normalized) > _TAG_NAME_MAX_LENGTH:
            raise CommunityTagNameTooLongError(_TAG_NAME_MAX_LENGTH)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class CommunityRuleTitle(ValueObject):
    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise CommunityRuleTitleRequiredError()
        if len(stripped) > _RULE_TITLE_MAX_LENGTH:
            raise CommunityRuleTitleTooLongError(_RULE_TITLE_MAX_LENGTH)
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value
