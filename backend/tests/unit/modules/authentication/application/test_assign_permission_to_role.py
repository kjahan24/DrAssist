"""Unit tests for the `AssignPermissionToRole` use case."""

from uuid import uuid4

import pytest

from app.modules.authentication.application.dto import AssignPermissionToRoleInput
from app.modules.authentication.application.use_cases.assign_permission_to_role import (
    AssignPermissionToRole,
)
from app.modules.authentication.domain.entities import Permission, Role
from app.modules.authentication.domain.exceptions import (
    PermissionCodeNotRegisteredError,
    RoleNotFoundError,
)
from app.modules.authentication.domain.value_objects import PermissionCode
from tests.unit.modules.authentication.application.fakes import (
    FakePermissionRepository,
    FakeRoleRepository,
    FakeUnitOfWork,
)


@pytest.fixture
def role_repository() -> FakeRoleRepository:
    return FakeRoleRepository()


@pytest.fixture
def permission_repository() -> FakePermissionRepository:
    return FakePermissionRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def use_case(
    role_repository: FakeRoleRepository,
    permission_repository: FakePermissionRepository,
    unit_of_work: FakeUnitOfWork,
) -> AssignPermissionToRole:
    return AssignPermissionToRole(
        role_repository=role_repository,
        permission_repository=permission_repository,
        unit_of_work=unit_of_work,
    )


class TestAssignPermissionToRole:
    async def test_grants_the_permission_to_the_role(
        self,
        use_case: AssignPermissionToRole,
        role_repository: FakeRoleRepository,
        permission_repository: FakePermissionRepository,
    ) -> None:
        role = Role.create(organization_id=uuid4(), name="Nurse")
        await role_repository.add(role)
        permission = Permission.create(
            code=PermissionCode("patients.read"), name="Read patients", description="Read"
        )
        await permission_repository.add(permission)

        output = await use_case.execute(
            AssignPermissionToRoleInput(role_id=role.id, permission_code="patients.read")
        )

        assert output.permission_id == permission.id
        updated_role = await role_repository.get_by_id(role.id)
        assert updated_role is not None
        assert updated_role.has_permission(permission.id)

    async def test_unknown_role_raises(
        self, use_case: AssignPermissionToRole, permission_repository: FakePermissionRepository
    ) -> None:
        permission = Permission.create(
            code=PermissionCode("patients.read"), name="Read patients", description="Read"
        )
        await permission_repository.add(permission)

        with pytest.raises(RoleNotFoundError):
            await use_case.execute(
                AssignPermissionToRoleInput(role_id=uuid4(), permission_code="patients.read")
            )

    async def test_unknown_permission_code_raises(
        self, use_case: AssignPermissionToRole, role_repository: FakeRoleRepository
    ) -> None:
        role = Role.create(organization_id=uuid4(), name="Nurse")
        await role_repository.add(role)

        with pytest.raises(PermissionCodeNotRegisteredError):
            await use_case.execute(
                AssignPermissionToRoleInput(role_id=role.id, permission_code="patients.read")
            )
