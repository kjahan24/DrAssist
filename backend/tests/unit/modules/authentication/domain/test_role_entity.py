"""Unit tests for the `Role` aggregate's invariants."""

from uuid import uuid4

import pytest

from app.modules.authentication.domain.entities import Role
from app.modules.authentication.domain.events import (
    PermissionGrantedToRole,
    PermissionRevokedFromRole,
    RoleActivated,
    RoleCreated,
    RoleDeactivated,
)
from app.modules.authentication.domain.exceptions import (
    InvalidRoleOrganizationScopeError,
    RoleNameRequiredError,
    SystemRoleImmutableError,
)


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

    def test_create_defaults_to_active(self) -> None:
        assert Role.create(organization_id=uuid4(), name="Nurse").is_active is True

    def test_blank_name_is_rejected(self) -> None:
        with pytest.raises(RoleNameRequiredError):
            Role.create(organization_id=uuid4(), name="   ")

    def test_name_is_stripped(self) -> None:
        role = Role.create(organization_id=uuid4(), name="  Nurse  ")
        assert role.name == "Nurse"

    def test_system_role_with_organization_id_is_rejected(self) -> None:
        with pytest.raises(InvalidRoleOrganizationScopeError):
            Role.create(organization_id=uuid4(), name="Doctor", is_system_role=True)

    def test_org_role_without_organization_id_is_rejected(self) -> None:
        with pytest.raises(InvalidRoleOrganizationScopeError):
            Role.create(organization_id=None, name="Front Desk", is_system_role=False)


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


class TestActivateDeactivate:
    def test_deactivate_sets_is_active_false_and_records_event(self) -> None:
        role = Role.create(organization_id=uuid4(), name="Nurse")
        role.pull_events()

        role.deactivate()

        assert role.is_active is False
        events = role.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], RoleDeactivated)

    def test_deactivating_an_already_inactive_role_is_idempotent(self) -> None:
        role = Role.create(organization_id=uuid4(), name="Nurse")
        role.deactivate()
        role.pull_events()

        role.deactivate()

        assert role.pull_events() == []

    def test_activate_sets_is_active_true_and_records_event(self) -> None:
        role = Role.create(organization_id=uuid4(), name="Nurse")
        role.deactivate()
        role.pull_events()

        role.activate()

        assert role.is_active is True
        events = role.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], RoleActivated)

    def test_activating_an_already_active_role_is_idempotent(self) -> None:
        role = Role.create(organization_id=uuid4(), name="Nurse")
        role.pull_events()

        role.activate()

        assert role.pull_events() == []

    def test_system_role_cannot_be_deactivated(self) -> None:
        role = Role.create(organization_id=None, name="Doctor", is_system_role=True)
        with pytest.raises(SystemRoleImmutableError):
            role.deactivate()

    def test_system_role_cannot_be_activated(self) -> None:
        role = Role.create(organization_id=None, name="Doctor", is_system_role=True)
        with pytest.raises(SystemRoleImmutableError):
            role.activate()
