"""Unit tests for the shared `Entity`/`AggregateRoot` base classes —
specifically the identity-equality behavior described in
`app/shared/domain/entity.py`'s `eq=False` docstring, since a regression
there (forgetting `eq=False` on a concrete subclass) would silently
reintroduce structural equality without any obviously-failing test
elsewhere.
"""

from dataclasses import dataclass
from uuid import uuid4

from app.shared.domain.domain_event import DomainEvent
from app.shared.domain.entity import AggregateRoot, Entity


@dataclass(kw_only=True, eq=False)
class _DummyEntity(Entity):
    name: str = "dummy"


@dataclass(kw_only=True, eq=False)
class _DummyAggregate(AggregateRoot):
    name: str = "dummy"


@dataclass(frozen=True, kw_only=True)
class _DummyEvent(DomainEvent):
    payload: str = "x"


class TestEntityIdentityEquality:
    def test_same_id_and_type_are_equal_regardless_of_other_fields(self) -> None:
        shared_id = uuid4()
        a = _DummyEntity(id=shared_id, name="a")
        b = _DummyEntity(id=shared_id, name="b")
        assert a == b
        assert hash(a) == hash(b)

    def test_different_ids_are_not_equal(self) -> None:
        assert _DummyEntity() != _DummyEntity()

    def test_same_id_but_different_type_are_not_equal(self) -> None:
        shared_id = uuid4()
        entity = _DummyEntity(id=shared_id)
        aggregate = _DummyAggregate(id=shared_id)
        assert entity != aggregate

    def test_equality_against_unrelated_type_is_not_equal(self) -> None:
        assert _DummyEntity() != "not-an-entity"

    def test_entities_are_usable_as_dict_keys(self) -> None:
        entity = _DummyEntity()
        registry = {entity: "value"}
        assert registry[_DummyEntity(id=entity.id)] == "value"


class TestAggregateRootEventCollection:
    def test_record_event_then_pull_events_returns_it_once(self) -> None:
        aggregate = _DummyAggregate()
        event = _DummyEvent(payload="hello")

        aggregate.record_event(event)

        assert aggregate.pull_events() == [event]
        assert aggregate.pull_events() == []

    def test_events_are_returned_in_recorded_order(self) -> None:
        aggregate = _DummyAggregate()
        first, second = _DummyEvent(payload="1"), _DummyEvent(payload="2")
        aggregate.record_event(first)
        aggregate.record_event(second)

        assert aggregate.pull_events() == [first, second]

    def test_touch_updates_updated_at(self) -> None:
        aggregate = _DummyAggregate()
        original = aggregate.updated_at
        aggregate.touch()
        assert aggregate.updated_at >= original

    def test_new_aggregates_start_with_no_pending_events(self) -> None:
        assert _DummyAggregate().pull_events() == []
