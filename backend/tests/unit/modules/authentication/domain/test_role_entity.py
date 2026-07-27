"""Unit tests for the `Role` aggregate's invariants."""

from uuid import uuid4

import pytest

from app.modules.authentication.domain.entities import Role
from app.modules.authentication.domain.events import (
    PermissionGrantedToRole,
    PermissionRevokedFromRole,
    RoleCreated,
)
from app.modules.authentication.domain.exceptions import SystemRoleImmutableError


class TestCreate:
    def test_create_records_role_created_event(self) -> None:
        org_id = uuid4()
        role = Role.create(organization_id=org_id, name="Front Desk")

        assert role.organization_id == org_id
        assert role.is_system_role is False
        events = role.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], RoleCreated)
        assert events[0].name == "Front Desk"

    def test_create_system_role_has_null_organization(self) -> None:
        role = Role.create(organization_id=None, name="Doctor", is_system_role=True)
        assert role.organization_id is None
        assert role.is_system_role is True


class TestPermissionGranting:
    def test_grant_permission_adds_id_and_records_event(self) -> None:
        role = Role.create(organization_id=uuid4(), name="Nurse")
        role.pull_events()
        permission_id = uuid4()

        role.grant_permission(permission_id)

        assert role.has_permission(permission_id) is True
        events = role.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PermissionGrantedToRole)

    def test_granting_an_already_granted_permission_is_idempotent(self) -> None:
        role = Role.create(organization_id=uuid4(), name="Nurse")
        permission_id = uuid4()
        role.grant_permission(permission_id)
        role.pull_events()

        role.grant_permission(permission_id)  # no-op: already present

        assert role.pull_events() == []

    def test_revoke_permission_removes_id_and_records_event(self) -> None:
        role = Role.create(organization_id=uuid4(), name="Nurse")
        permission_id = uuid4()
        role.grant_permission(permission_id)
        role.pull_events()

        role.revoke_permission(permission_id)

        assert role.has_permission(permission_id) is False
        events = role.pull_events()
        assert any(isinstance(e, PermissionRevokedFromRole) for e in events)

    def test_revoking_a_permission_not_held_is_idempotent(self) -> None:
        role = Role.create(organization_id=uuid4(), name="Nurse")
        role.pull_events()
        role.revoke_permission(uuid4())
        assert role.pull_events() == []

    def test_system_role_permissions_cannot_be_granted(self) -> None:
        role = Role.create(organization_id=None, name="Doctor", is_system_role=True)
        with pytest.raises(SystemRoleImmutableError):
            role.grant_permission(uuid4())

    def test_system_role_permissions_cannot_be_revoked(self) -> None:
        role = Role.create(organization_id=None, name="Doctor", is_system_role=True)
        with pytest.raises(SystemRoleImmutableError):
            role.revoke_permission(uuid4())
