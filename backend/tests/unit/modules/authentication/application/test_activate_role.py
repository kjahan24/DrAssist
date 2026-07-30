"""Unit tests for the `ActivateRole` use case."""

from uuid import uuid4

import pytest

from app.modules.authentication.application.dto import ActivateRoleInput
from app.modules.authentication.application.use_cases.activate_role import ActivateRole
from app.modules.authentication.domain.entities import Role
from app.modules.authentication.domain.exceptions import RoleNotFoundError, SystemRoleImmutableError
from tests.unit.modules.authentication.application.fakes import FakeRoleRepository, FakeUnitOfWork


@pytest.fixture
def role_repository() -> FakeRoleRepository:
    return FakeRoleRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def use_case(role_repository: FakeRoleRepository, unit_of_work: FakeUnitOfWork) -> ActivateRole:
    return ActivateRole(role_repository=role_repository, unit_of_work=unit_of_work)


class TestActivateRole:
    async def test_activates_an_inactive_role(
        self, use_case: ActivateRole, role_repository: FakeRoleRepository
    ) -> None:
        role = Role.create(organization_id=uuid4(), name="Nurse")
        role.deactivate()
        await role_repository.add(role)

        output = await use_case.execute(ActivateRoleInput(role_id=role.id))

        assert output.is_active is True

    async def test_unknown_role_raises(self, use_case: ActivateRole) -> None:
        with pytest.raises(RoleNotFoundError):
            await use_case.execute(ActivateRoleInput(role_id=uuid4()))

    async def test_system_role_cannot_be_activated(
        self, use_case: ActivateRole, role_repository: FakeRoleRepository
    ) -> None:
        role = Role.create(organization_id=None, name="Doctor", is_system_role=True)
        await role_repository.add(role)

        with pytest.raises(SystemRoleImmutableError):
            await use_case.execute(ActivateRoleInput(role_id=role.id))
