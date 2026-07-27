"""Unit tests for `Permission` — minimal, since it carries no behavior
beyond construction (a global, migration-seeded catalog entry)."""

from app.modules.authentication.domain.entities import Permission
from app.modules.authentication.domain.value_objects import PermissionCode


class TestCreate:
    def test_create_builds_a_permission_with_the_given_code(self) -> None:
        permission = Permission.create(
            code=PermissionCode("patients.read"),
            module="patients",
            description="Read patient records",
        )
        assert str(permission.code) == "patients.read"
        assert permission.module == "patients"

    def test_create_records_no_events(self) -> None:
        permission = Permission.create(
            code=PermissionCode("patients.write"), module="patients", description="Write"
        )
        assert permission.pull_events() == []
