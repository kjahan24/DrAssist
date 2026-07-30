"""Unit tests for `PermissionQueryService`."""

from uuid import uuid4

from app.modules.authentication.application.services.permission_query_service import (
    PermissionQueryService,
)
from app.modules.authentication.domain.entities import Permission
from app.modules.authentication.domain.value_objects import PermissionCode
from tests.unit.modules.authentication.application.fakes import FakePermissionRepository


class TestPermissionExists:
    async def test_true_for_a_stored_permission(self) -> None:
        repo = FakePermissionRepository()
        permission = Permission.create(code=PermissionCode("patients.read"), name="Read patients")
        await repo.add(permission)
        service = PermissionQueryService(permission_repository=repo)

        assert await service.permission_exists(permission.id) is True

    async def test_false_for_an_unknown_permission(self) -> None:
        service = PermissionQueryService(permission_repository=FakePermissionRepository())
        assert await service.permission_exists(uuid4()) is False


class TestGetPermissionSummary:
    async def test_returns_a_summary_with_derived_resource_and_action(self) -> None:
        repo = FakePermissionRepository()
        permission = Permission.create(
            code=PermissionCode("patients.read"), name="Read patients", description="Read"
        )
        await repo.add(permission)
        service = PermissionQueryService(permission_repository=repo)

        summary = await service.get_permission_summary(permission.id)

        assert summary is not None
        assert summary.code == "patients.read"
        assert summary.resource == "patients"
        assert summary.action == "read"

    async def test_returns_none_for_an_unknown_permission(self) -> None:
        service = PermissionQueryService(permission_repository=FakePermissionRepository())
        assert await service.get_permission_summary(uuid4()) is None


class TestGetPermissionByCode:
    async def test_returns_the_matching_permission(self) -> None:
        repo = FakePermissionRepository()
        permission = Permission.create(code=PermissionCode("patients.read"), name="Read patients")
        await repo.add(permission)
        service = PermissionQueryService(permission_repository=repo)

        summary = await service.get_permission_by_code("patients.read")

        assert summary is not None and summary.permission_id == permission.id

    async def test_returns_none_for_an_unmatched_code(self) -> None:
        service = PermissionQueryService(permission_repository=FakePermissionRepository())
        assert await service.get_permission_by_code("patients.read") is None


class TestListAllPermissions:
    async def test_returns_every_stored_permission(self) -> None:
        repo = FakePermissionRepository()
        first = Permission.create(code=PermissionCode("patients.read"), name="Read patients")
        second = Permission.create(code=PermissionCode("patients.write"), name="Write patients")
        await repo.add(first)
        await repo.add(second)
        service = PermissionQueryService(permission_repository=repo)

        results = await service.list_all_permissions()

        assert {r.permission_id for r in results} == {first.id, second.id}


class TestListPermissionsForRole:
    async def test_returns_only_permissions_seeded_for_that_role(self) -> None:
        repo = FakePermissionRepository()
        role_id = uuid4()
        granted = Permission.create(code=PermissionCode("patients.read"), name="Read patients")
        ungranted = Permission.create(code=PermissionCode("patients.write"), name="Write patients")
        await repo.add(granted)
        await repo.add(ungranted)
        repo.seed_role_permission(role_id, granted.id)
        service = PermissionQueryService(permission_repository=repo)

        results = await service.list_permissions_for_role(role_id)

        assert [r.permission_id for r in results] == [granted.id]
