"""Unit tests for `RoleQueryService`."""

from uuid import uuid4

from app.modules.authentication.application.services.role_query_service import RoleQueryService
from app.modules.authentication.domain.entities import Role
from tests.unit.modules.authentication.application.fakes import FakeRoleRepository


class TestRoleExists:
    async def test_true_for_a_stored_role(self) -> None:
        repo = FakeRoleRepository()
        role = Role.create(organization_id=uuid4(), name="Nurse")
        await repo.add(role)
        service = RoleQueryService(role_repository=repo)

        assert await service.role_exists(role.id) is True

    async def test_false_for_an_unknown_role(self) -> None:
        service = RoleQueryService(role_repository=FakeRoleRepository())
        assert await service.role_exists(uuid4()) is False


class TestGetRoleSummary:
    async def test_returns_a_summary_for_a_stored_role(self) -> None:
        repo = FakeRoleRepository()
        role = Role.create(organization_id=uuid4(), name="Nurse", description="Ward nurse")
        await repo.add(role)
        service = RoleQueryService(role_repository=repo)

        summary = await service.get_role_summary(role.id)

        assert summary is not None
        assert summary.role_id == role.id
        assert summary.name == "Nurse"
        assert summary.description == "Ward nurse"
        assert summary.is_active is True

    async def test_returns_none_for_an_unknown_role(self) -> None:
        service = RoleQueryService(role_repository=FakeRoleRepository())
        assert await service.get_role_summary(uuid4()) is None


class TestListRolesForOrganization:
    async def test_returns_only_that_organizations_roles(self) -> None:
        repo = FakeRoleRepository()
        org_id = uuid4()
        mine = Role.create(organization_id=org_id, name="Nurse")
        other = Role.create(organization_id=uuid4(), name="Billing")
        await repo.add(mine)
        await repo.add(other)
        service = RoleQueryService(role_repository=repo)

        results = await service.list_roles_for_organization(org_id)

        assert [r.role_id for r in results] == [mine.id]

    async def test_returns_empty_list_for_an_organization_without_roles(self) -> None:
        service = RoleQueryService(role_repository=FakeRoleRepository())
        assert await service.list_roles_for_organization(uuid4()) == []


class TestListSystemRoles:
    async def test_returns_only_system_roles(self) -> None:
        repo = FakeRoleRepository()
        system_role = Role.create(organization_id=None, name="Doctor", is_system_role=True)
        org_role = Role.create(organization_id=uuid4(), name="Nurse")
        await repo.add(system_role)
        await repo.add(org_role)
        service = RoleQueryService(role_repository=repo)

        results = await service.list_system_roles()

        assert [r.role_id for r in results] == [system_role.id]
