"""Value objects specific to the Medical Topics module.

`TopicId` mirrors `app.modules.community.domain.value_objects.CommunityId`
exactly — a strongly-typed wrapper used only as the cross-aggregate
*reference* field (`MedicalTopicFollower.topic_id`,
`MedicalTopicAlias.topic_id`, `MedicalTopicRelation.topic_id`), never as
`MedicalTopic.id` itself (which stays a plain `UUID`, like every other
aggregate root — see that module's own docstring for the full reasoning,
identical here).
"""

import re
from dataclasses import dataclass
from uuid import UUID

from app.modules.medical_topics.domain.exceptions import (
    InvalidTopicColorError,
    InvalidTopicSlugError,
    TopicDescriptionRequiredError,
    TopicDescriptionTooLongError,
    TopicNameRequiredError,
    TopicNameTooLongError,
)
from app.shared.domain.value_object import ValueObject

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_MIN_LENGTH = 3
_SLUG_MAX_LENGTH = 64
_NAME_MAX_LENGTH = 200
_DESCRIPTION_MAX_LENGTH = 2000
_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True, slots=True)
class TopicId(ValueObject):
    value: UUID

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class TopicSlug(ValueObject):
    """A URL-safe, platform-wide-unique identifier, e.g.
    `"cardiac-arrhythmia"`. Normalized to lowercase (trimmed of
    surrounding whitespace) so lookups are case-insensitive without a
    `CITEXT` column — the same normalize-in-the-value-object approach
    `CommunitySlug` already establishes for itself."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not (_SLUG_MIN_LENGTH <= len(normalized) <= _SLUG_MAX_LENGTH) or not _SLUG_PATTERN.match(
            normalized
        ):
            raise InvalidTopicSlugError(self.value)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class TopicName(ValueObject):
    """Also reused for `MedicalTopicAlias.alias` and
    `TopicSpecialty.name` — an alias/synonym and a specialty name are
    both, structurally, just "a validated topic-vocabulary name," so
    reusing this value object avoids two near-identical duplicates (see
    `MedicalTopicAlias`'s own docstring)."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise TopicNameRequiredError()
        if len(stripped) > _NAME_MAX_LENGTH:
            raise TopicNameTooLongError(_NAME_MAX_LENGTH)
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class TopicDescription(ValueObject):
    """Optional free text — `MedicalTopic.description` is
    `TopicDescription | None`, never an empty-string `TopicDescription`;
    a caller with nothing to say passes `None`, not a blank description
    (the same rule `CommunityDescription` already follows)."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise TopicDescriptionRequiredError()
        if len(stripped) > _DESCRIPTION_MAX_LENGTH:
            raise TopicDescriptionTooLongError(_DESCRIPTION_MAX_LENGTH)
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class TopicColor(ValueObject):
    """A `#RRGGBB` hex color swatch (e.g. `"#FF5733"`) used to render a
    topic's UI accent color — normalized to uppercase on construction so
    `"#ff5733"` and `"#FF5733"` compare equal."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not _COLOR_PATTERN.match(stripped):
            raise InvalidTopicColorError(self.value)
        object.__setattr__(self, "value", stripped.upper())

    def __str__(self) -> str:
        return self.value
