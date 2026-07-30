"""Unit tests for the `DeactivateRole` use case."""

from uuid import uuid4

import pytest

from app.modules.authentication.application.dto import DeactivateRoleInput
from app.modules.authentication.application.use_cases.deactivate_role import DeactivateRole
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
def use_case(role_repository: FakeRoleRepository, unit_of_work: FakeUnitOfWork) -> DeactivateRole:
    return DeactivateRole(role_repository=role_repository, unit_of_work=unit_of_work)


class TestDeactivateRole:
    async def test_deactivates_an_active_role(
        self, use_case: DeactivateRole, role_repository: FakeRoleRepository
    ) -> None:
        role = Role.create(organization_id=uuid4(), name="Nurse")
        await role_repository.add(role)

        output = await use_case.execute(DeactivateRoleInput(role_id=role.id))

        assert output.is_active is False

    async def test_unknown_role_raises(self, use_case: DeactivateRole) -> None:
        with pytest.raises(RoleNotFoundError):
            await use_case.execute(DeactivateRoleInput(role_id=uuid4()))

    async def test_system_role_cannot_be_deactivated(
        self, use_case: DeactivateRole, role_repository: FakeRoleRepository
    ) -> None:
        role = Role.create(organization_id=None, name="Doctor", is_system_role=True)
        await role_repository.add(role)

        with pytest.raises(SystemRoleImmutableError):
            await use_case.execute(DeactivateRoleInput(role_id=role.id))
