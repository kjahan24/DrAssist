"""Unit tests for `Permission` — minimal, since it carries little behavior
beyond construction (a global, admin-created catalog entry)."""

import pytest

from app.modules.authentication.domain.entities import Permission
from app.modules.authentication.domain.events import PermissionCreated
from app.modules.authentication.domain.exceptions import PermissionNameRequiredError
from app.modules.authentication.domain.value_objects import PermissionCode


class TestCreate:
    def test_create_builds_a_permission_with_the_given_code(self) -> None:
        permission = Permission.create(
            code=PermissionCode("patients.read"),
            name="Read patients",
            description="Read patient records",
        )
        assert str(permission.code) == "patients.read"
        assert permission.name == "Read patients"

    def test_resource_and_action_are_derived_from_the_code(self) -> None:
        permission = Permission.create(code=PermissionCode("patients.read"), name="Read patients")
        assert permission.resource == "patients"
        assert permission.action == "read"

    def test_description_defaults_to_none(self) -> None:
        permission = Permission.create(code=PermissionCode("patients.write"), name="Write patients")
        assert permission.description is None

    def test_blank_name_is_rejected(self) -> None:
        with pytest.raises(PermissionNameRequiredError):
            Permission.create(code=PermissionCode("patients.write"), name="   ")

    def test_create_records_permission_created_event(self) -> None:
        permission = Permission.create(code=PermissionCode("patients.write"), name="Write patients")
        events = permission.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PermissionCreated)
        assert events[0].code == "patients.write"
