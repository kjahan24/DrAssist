"""Integration tests for `SqlAlchemyRoleRepository`, including the
`role_permissions`/`user_roles` association tables, the partial unique
indexes backing "role names must be unique within an organization" /
"global system role names must be unique", the `is_active` column added
for this task, and the `system_role_organization_scope` `CHECK`
constraint, against a real PostgreSQL instance.

Every role name/permission code below is suffixed with `unique_suffix()`
— `uq_roles_system_name`/`uq_permissions_code` are *globally* unique
(not scoped to a test), and this suite runs against a real, persistent
database with no per-test rollback, so a bare literal like `"Doctor"`
reused across two tests that both commit would collide exactly like a
real duplicate — the same reasoning
`tests.integration.modules.appointment._helpers` already documents for
its own `f"APT-{uuid4().hex[:12].upper()}"` pattern.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.authentication._helpers import persist_user, unique_suffix

from app.modules.authentication.domain.entities import Permission, Role
from app.modules.authentication.domain.value_objects import PermissionCode
from app.modules.authentication.infrastructure.models import RoleModel
from app.modules.authentication.infrastructure.repositories import (
    SqlAlchemyPermissionRepository,
    SqlAlchemyRoleRepository,
)


class TestRoleRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyRoleRepository(db_session)
        org_id = uuid4()

        role = Role.create(
            organization_id=org_id, name=f"Nurse-{unique_suffix()}", description="Ward nurse"
        )
        await repo.add(role)
        await db_session.commit()

        reloaded = await repo.get_by_id(role.id)
        assert reloaded is not None
        assert reloaded.organization_id == org_id
        assert reloaded.name == role.name
        assert reloaded.description == "Ward nurse"
        assert reloaded.is_system_role is False
        assert reloaded.is_active is True

    async def test_deactivated_role_persists_is_active_false(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyRoleRepository(db_session)
        role = Role.create(organization_id=uuid4(), name=f"Billing-{unique_suffix()}")
        await repo.add(role)
        await db_session.commit()

        role.deactivate()
        await repo.add(role)
        await db_session.commit()

        reloaded = await repo.get_by_id(role.id)
        assert reloaded is not None
        assert reloaded.is_active is False

    async def test_grant_and_revoke_permission_persists_via_role_permissions(
        self, db_session: AsyncSession
    ) -> None:
        role_repo = SqlAlchemyRoleRepository(db_session)
        permission_repo = SqlAlchemyPermissionRepository(db_session)
        suffix = unique_suffix()

        permission_a = Permission.create(
            code=PermissionCode(f"patients_{suffix}.read"), name="Read"
        )
        permission_b = Permission.create(
            code=PermissionCode(f"patients_{suffix}.write"), name="Write"
        )
        await permission_repo.add(permission_a)
        await permission_repo.add(permission_b)
        await db_session.commit()

        role = Role.create(organization_id=uuid4(), name=f"Nurse-{suffix}")
        role.grant_permission(permission_a.id)
        role.grant_permission(permission_b.id)
        await role_repo.add(role)
        await db_session.commit()

        reloaded = await role_repo.get_by_id(role.id)
        assert reloaded is not None
        assert reloaded.permission_ids == {permission_a.id, permission_b.id}

        reloaded.revoke_permission(permission_a.id)
        await role_repo.add(reloaded)
        await db_session.commit()

        reloaded_again = await role_repo.get_by_id(role.id)
        assert reloaded_again is not None
        assert reloaded_again.permission_ids == {permission_b.id}


class TestGetByName:
    async def test_get_system_role_by_name_finds_the_matching_role(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyRoleRepository(db_session)
        name = f"Doctor-{unique_suffix()}"
        role = Role.create(organization_id=None, name=name, is_system_role=True)
        await repo.add(role)
        await db_session.commit()

        found = await repo.get_system_role_by_name(name)
        assert found is not None and found.id == role.id

    async def test_get_org_role_by_name_finds_the_matching_role(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyRoleRepository(db_session)
        org_id = uuid4()
        name = f"Front Desk-{unique_suffix()}"
        role = Role.create(organization_id=org_id, name=name)
        await repo.add(role)
        await db_session.commit()

        found = await repo.get_org_role_by_name(organization_id=org_id, name=name)
        assert found is not None and found.id == role.id

    async def test_get_org_role_by_name_does_not_match_a_different_organization(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyRoleRepository(db_session)
        name = f"Front Desk-{unique_suffix()}"
        role = Role.create(organization_id=uuid4(), name=name)
        await repo.add(role)
        await db_session.commit()

        assert await repo.get_org_role_by_name(organization_id=uuid4(), name=name) is None


class TestListQueries:
    async def test_list_by_organization_returns_only_that_organizations_roles(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyRoleRepository(db_session)
        org_id = uuid4()
        suffix = unique_suffix()
        mine = Role.create(organization_id=org_id, name=f"Nurse-{suffix}")
        other = Role.create(organization_id=uuid4(), name=f"Billing-{suffix}")
        await repo.add(mine)
        await repo.add(other)
        await db_session.commit()

        results = await repo.list_by_organization(org_id)
        assert [r.id for r in results] == [mine.id]

    async def test_list_system_roles_returns_only_system_roles(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyRoleRepository(db_session)
        suffix = unique_suffix()
        system_role = Role.create(
            organization_id=None, name=f"SuperAdmin-{suffix}", is_system_role=True
        )
        org_role = Role.create(organization_id=uuid4(), name=f"Nurse-{suffix}")
        await repo.add(system_role)
        await repo.add(org_role)
        await db_session.commit()

        results = await repo.list_system_roles()
        assert system_role.id in {r.id for r in results}
        assert org_role.id not in {r.id for r in results}


class TestUserRoleAssignment:
    async def test_assign_to_user_makes_role_visible_via_list_for_user(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyRoleRepository(db_session)
        org_id = uuid4()
        user = await persist_user(db_session, organization_id=org_id)
        role = Role.create(organization_id=org_id, name=f"Nurse-{unique_suffix()}")
        await repo.add(role)
        await db_session.commit()

        await repo.assign_to_user(
            organization_id=org_id,
            user_id=user.id,
            role_id=role.id,
            granted_by=None,
            granted_at=datetime.now(UTC),
        )
        await db_session.commit()

        assigned = await repo.list_for_user(user.id)
        assert [r.id for r in assigned] == [role.id]
        assert await repo.is_assigned_to_user(user_id=user.id, role_id=role.id) is True

    async def test_assigning_the_same_role_twice_is_idempotent(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyRoleRepository(db_session)
        org_id = uuid4()
        user = await persist_user(db_session, organization_id=org_id)
        role = Role.create(organization_id=org_id, name=f"Nurse-{unique_suffix()}")
        await repo.add(role)
        await db_session.commit()

        for _ in range(2):
            await repo.assign_to_user(
                organization_id=org_id,
                user_id=user.id,
                role_id=role.id,
                granted_by=None,
                granted_at=datetime.now(UTC),
            )
            await db_session.commit()

        assigned = await repo.list_for_user(user.id)
        assert [r.id for r in assigned] == [role.id]

    async def test_revoke_from_user_removes_the_assignment(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyRoleRepository(db_session)
        org_id = uuid4()
        user = await persist_user(db_session, organization_id=org_id)
        role = Role.create(organization_id=org_id, name=f"Nurse-{unique_suffix()}")
        await repo.add(role)
        await db_session.commit()
        await repo.assign_to_user(
            organization_id=org_id,
            user_id=user.id,
            role_id=role.id,
            granted_by=None,
            granted_at=datetime.now(UTC),
        )
        await db_session.commit()

        await repo.revoke_from_user(user_id=user.id, role_id=role.id)
        await db_session.commit()

        assert await repo.is_assigned_to_user(user_id=user.id, role_id=role.id) is False


class TestDelete:
    async def test_delete_soft_deletes_the_role(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyRoleRepository(db_session)
        role = Role.create(organization_id=uuid4(), name=f"Nurse-{unique_suffix()}")
        await repo.add(role)
        await db_session.commit()

        await repo.delete(role.id)
        await db_session.commit()

        assert await repo.get_by_id(role.id) is None

    async def test_deleting_an_unknown_role_is_a_no_op(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyRoleRepository(db_session)
        await repo.delete(uuid4())
        await db_session.commit()


class TestUniqueRoleNames:
    """`SqlAlchemyRoleRepository.add()` runs a `SELECT` against
    `role_permissions` right after staging the pending `INSERT` (to diff
    `Role.permission_ids` against the existing association rows) — that
    `SELECT` triggers SQLAlchemy's autoflush, which flushes the pending
    `INSERT` (and therefore any constraint violation) *inside* `add()`
    itself, before an explicit `commit()` would. `pytest.raises` below
    wraps the second `add()` call, not `commit()`, to match this.
    """

    async def test_duplicate_system_role_name_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyRoleRepository(db_session)
        name = f"Doctor-{unique_suffix()}"
        await repo.add(Role.create(organization_id=None, name=name, is_system_role=True))
        await db_session.commit()

        with pytest.raises(IntegrityError):
            await repo.add(Role.create(organization_id=None, name=name, is_system_role=True))
        await db_session.rollback()

    async def test_duplicate_org_role_name_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyRoleRepository(db_session)
        org_id = uuid4()
        name = f"Nurse-{unique_suffix()}"
        await repo.add(Role.create(organization_id=org_id, name=name))
        await db_session.commit()

        with pytest.raises(IntegrityError):
            await repo.add(Role.create(organization_id=org_id, name=name))
        await db_session.rollback()

    async def test_same_name_in_different_organizations_is_allowed(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyRoleRepository(db_session)
        name = f"Nurse-{unique_suffix()}"
        await repo.add(Role.create(organization_id=uuid4(), name=name))
        await repo.add(Role.create(organization_id=uuid4(), name=name))
        await db_session.commit()


class TestCheckConstraints:
    """`Role.__post_init__` already prevents `is_system_role`/
    `organization_id` from ever mismatching via the domain layer — this
    test targets the DB `CHECK` constraint directly (bypassing the domain
    entity, the way a direct SQL edit would) to prove the
    defense-in-depth layer actually works, the same pattern
    `tests.integration.modules.appointment.test_appointment_repository
    .TestCheckConstraints` already established.
    """

    async def test_system_role_with_organization_id_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        model = RoleModel(
            organization_id=uuid4(),
            name=f"Doctor-{unique_suffix()}",
            is_system_role=True,
            is_active=True,
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_org_role_without_organization_id_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        model = RoleModel(
            organization_id=None,
            name=f"Front Desk-{unique_suffix()}",
            is_system_role=False,
            is_active=True,
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
