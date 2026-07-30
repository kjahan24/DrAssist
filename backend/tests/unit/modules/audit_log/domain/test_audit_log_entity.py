"""Unit tests for the `AuditLog` entity's own invariants: blank
`entity_type` rejection, optional fields defaulting to `None`, and that
`record()` never records any domain event (see the entity's own
docstring for why)."""

from uuid import uuid4

import pytest

from app.modules.audit_log.domain.entities import AuditLog
from app.modules.audit_log.domain.enums import AuditAction, AuditSource
from app.modules.audit_log.domain.exceptions import EntityTypeRequiredError


def _make_audit_log(**overrides: object) -> AuditLog:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "entity_type": "Appointment",
        "entity_id": uuid4(),
        "action": AuditAction.CREATE,
        "source": AuditSource.API,
    }
    defaults.update(overrides)
    return AuditLog.record(**defaults)  # type: ignore[arg-type]


class TestRecord:
    def test_record_sets_identity_fields(self) -> None:
        organization_id = uuid4()
        entity_id = uuid4()

        audit_log = _make_audit_log(
            organization_id=organization_id,
            entity_type="Appointment",
            entity_id=entity_id,
            action=AuditAction.UPDATE,
            source=AuditSource.API,
        )

        assert audit_log.organization_id == organization_id
        assert audit_log.entity_type == "Appointment"
        assert audit_log.entity_id == entity_id
        assert audit_log.action is AuditAction.UPDATE
        assert audit_log.source is AuditSource.API

    def test_blank_entity_type_is_rejected(self) -> None:
        with pytest.raises(EntityTypeRequiredError):
            _make_audit_log(entity_type="   ")

    def test_entity_type_is_stripped(self) -> None:
        audit_log = _make_audit_log(entity_type="  Appointment  ")
        assert audit_log.entity_type == "Appointment"

    def test_actor_user_id_defaults_to_none(self) -> None:
        assert _make_audit_log().actor_user_id is None

    def test_actor_user_id_can_be_set(self) -> None:
        actor_user_id = uuid4()
        audit_log = _make_audit_log(actor_user_id=actor_user_id)
        assert audit_log.actor_user_id == actor_user_id

    def test_optional_fields_default_to_none(self) -> None:
        audit_log = _make_audit_log()
        assert audit_log.old_values is None
        assert audit_log.new_values is None
        assert audit_log.ip_address is None
        assert audit_log.user_agent is None
        assert audit_log.request_id is None
        assert audit_log.correlation_id is None

    def test_old_and_new_values_are_preserved(self) -> None:
        audit_log = _make_audit_log(
            action=AuditAction.UPDATE,
            old_values={"status": "scheduled"},
            new_values={"status": "confirmed"},
        )
        assert audit_log.old_values == {"status": "scheduled"}
        assert audit_log.new_values == {"status": "confirmed"}

    def test_context_fields_are_preserved(self) -> None:
        audit_log = _make_audit_log(
            ip_address="203.0.113.5",
            user_agent="Mozilla/5.0",
            request_id="req-123",
            correlation_id="corr-456",
        )
        assert audit_log.ip_address == "203.0.113.5"
        assert audit_log.user_agent == "Mozilla/5.0"
        assert audit_log.request_id == "req-123"
        assert audit_log.correlation_id == "corr-456"

    def test_created_at_is_set(self) -> None:
        assert _make_audit_log().created_at is not None

    def test_record_has_no_mutation_methods(self) -> None:
        """ "Audit logs are immutable" / "can never be updated" — the only
        callable on this class is the `record()` factory itself; this
        test documents that fact rather than exercising behavior."""
        audit_log = _make_audit_log()
        public_methods = [
            name
            for name in dir(audit_log)
            if not name.startswith("_") and callable(getattr(audit_log, name))
        ]
        assert public_methods == ["record"]
