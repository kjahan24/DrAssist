"""Unit tests for the `DeleteRole` use case."""

from uuid import uuid4

import pytest

from app.modules.authentication.application.dto import DeleteRoleInput
from app.modules.authentication.application.use_cases.delete_role import DeleteRole
from app.modules.authentication.domain.entities import Role
from app.modules.authentication.domain.events import RoleDeleted
from app.modules.authentication.domain.exceptions import RoleNotFoundError, SystemRoleImmutableError
from tests.unit.modules.authentication.application.fakes import FakeRoleRepository, FakeUnitOfWork


@pytest.fixture
def role_repository() -> FakeRoleRepository:
    return FakeRoleRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def use_case(role_repository: FakeRoleRepository, unit_of_work: FakeUnitOfWork) -> DeleteRole:
    return DeleteRole(role_repository=role_repository, unit_of_work=unit_of_work)


class TestDeleteRole:
    async def test_deletes_an_org_role(
        self,
        use_case: DeleteRole,
        role_repository: FakeRoleRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        role = Role.create(organization_id=uuid4(), name="Nurse")
        await role_repository.add(role)

        await use_case.execute(DeleteRoleInput(role_id=role.id))

        assert await role_repository.get_by_id(role.id) is None
        assert unit_of_work.committed is True
        assert any(isinstance(e, RoleDeleted) for e in unit_of_work.published_events)

    async def test_unknown_role_raises(self, use_case: DeleteRole) -> None:
        with pytest.raises(RoleNotFoundError):
            await use_case.execute(DeleteRoleInput(role_id=uuid4()))

    async def test_system_role_cannot_be_deleted(
        self, use_case: DeleteRole, role_repository: FakeRoleRepository
    ) -> None:
        role = Role.create(organization_id=None, name="Doctor", is_system_role=True)
        await role_repository.add(role)

        with pytest.raises(SystemRoleImmutableError):
            await use_case.execute(DeleteRoleInput(role_id=role.id))

        assert await role_repository.get_by_id(role.id) is not None
