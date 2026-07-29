"""Enums owned by the Lab Orders module's domain.

`LabOrderStatus` is reused as the type of *both* `LabOrder.status` and
`LabOrderItem.status` — this task's own field list gives `LabOrderItem` a
`status` field but defines only one status enum, and nothing in the
business rules describes a distinct item-level vocabulary, so introducing
a second, unrequested enum would be scope creep. A panel with multiple
tests plausibly has each item track collection independently (one tube
drawn before another), which this reuse already supports without any
extra type.
"""

from enum import StrEnum


class Priority(StrEnum):
    ROUTINE = "routine"
    URGENT = "urgent"
    STAT = "stat"


class LabOrderStatus(StrEnum):
    DRAFT = "draft"
    ORDERED = "ordered"
    COLLECTED = "collected"
    CANCELLED = "cancelled"
