"""Marker base for value objects.

A value object has no identity — equality is by value, not by `id`, and
instances are immutable. Concrete value objects are `@dataclass(frozen=True,
slots=True)` subclasses that validate themselves in `__post_init__` and
raise on construction if the value is invalid, so an invalid value object
can never exist in memory (see
`docs/backend-architecture/04_repository_and_service_patterns.md`, Tier 3
validation). This base carries no fields — it exists purely so `isinstance`
checks and type hints can refer to "any value object" generically.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValueObject:
    pass
