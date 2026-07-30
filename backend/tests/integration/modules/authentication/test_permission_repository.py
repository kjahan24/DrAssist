"""Integration tests for `SqlAlchemyPermissionRepository`, including the
`module` -> `resource` rename, the new `name`/`action` columns, the
nullable `description` column, and the `uq_permissions_code` partial
unique index, against a real PostgreSQL instance.

Every permission code is suffixed with `unique_suffix()` — `code` is
*globally* unique, and this suite runs against a real, persistent
database with no per-test rollback, so a bare literal like
`"patients.read"` reused across two tests that both commit would collide
exactly like a real duplicate.
"""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.authentication._helpers import unique_suffix

from app.modules.authentication.domain.entities import Permission, Role
from app.modules.authentication.domain.value_objects import PermissionCode
from app.modules.authentication.infrastructure.repositories import (
    SqlAlchemyPermissionRepository,
    SqlAlchemyRoleRepository,
)


class TestPermissionRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyPermissionRepository(db_session)
        code = f"patients_{unique_suffix()}.read"

        permission = Permission.create(
            code=PermissionCode(code),
            name="Read patients",
            description="Read patient records",
        )
        await repo.add(permission)
        await db_session.commit()

        reloaded = await repo.get_by_id(permission.id)
        assert reloaded is not None
        assert str(reloaded.code) == code
        assert reloaded.name == "Read patients"
        assert reloaded.resource == code.split(".")[0]
        assert reloaded.action == "read"
        assert reloaded.description == "Read patient records"

    async def test_description_defaults_to_none(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyPermissionRepository(db_session)
        permission = Permission.create(
            code=PermissionCode(f"patients_{unique_suffix()}.write"), name="Write patients"
        )
        await repo.add(permission)
        await db_session.commit()

        reloaded = await repo.get_by_id(permission.id)
        assert reloaded is not None
        assert reloaded.description is None


class TestGetByCode:
    async def test_returns_the_matching_permission(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyPermissionRepository(db_session)
        code = f"patients_{unique_suffix()}.read"
        permission = Permission.create(code=PermissionCode(code), name="Read patients")
        await repo.add(permission)
        await db_session.commit()

        found = await repo.get_by_code(code)
        assert found is not None and found.id == permission.id

    async def test_returns_none_for_an_unmatched_code(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyPermissionRepository(db_session)
        assert await repo.get_by_code(f"patients_{unique_suffix()}.missing") is None


class TestListAll:
    async def test_returns_every_stored_permission_ordered_by_resource_then_code(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyPermissionRepository(db_session)
        resource = f"patients_{unique_suffix()}"
        write = Permission.create(code=PermissionCode(f"{resource}.write"), name="Write patients")
        read = Permission.create(code=PermissionCode(f"{resource}.read"), name="Read patients")
        await repo.add(write)
        await repo.add(read)
        await db_session.commit()

        results = await repo.list_all()
        codes = [str(p.code) for p in results]
        assert codes.index(f"{resource}.read") < codes.index(f"{resource}.write")


class TestListForRole:
    async def test_returns_only_permissions_granted_to_the_role(
        self, db_session: AsyncSession
    ) -> None:
        permission_repo = SqlAlchemyPermissionRepository(db_session)
        role_repo = SqlAlchemyRoleRepository(db_session)
        resource = f"patients_{unique_suffix()}"

        granted = Permission.create(code=PermissionCode(f"{resource}.read"), name="Read patients")
        ungranted = Permission.create(
            code=PermissionCode(f"{resource}.write"), name="Write patients"
        )
        await permission_repo.add(granted)
        await permission_repo.add(ungranted)
        await db_session.commit()

        role = Role.create(organization_id=uuid4(), name=f"Nurse-{unique_suffix()}")
        role.grant_permission(granted.id)
        await role_repo.add(role)
        await db_session.commit()

        results = await permission_repo.list_for_role(role.id)
        assert [p.id for p in results] == [granted.id]


class TestUniquePermissionCode:
    async def test_duplicate_code_violates_unique_index(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyPermissionRepository(db_session)
        code = f"patients_{unique_suffix()}.read"
        await repo.add(Permission.create(code=PermissionCode(code), name="Read"))
        await db_session.commit()

        await repo.add(Permission.create(code=PermissionCode(code), name="Read again"))
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
