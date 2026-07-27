"""Unit tests for the `CreateRole` use case, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.authentication.application.dto import CreateRoleInput
from app.modules.authentication.application.use_cases.create_role import CreateRole
from app.modules.authentication.domain.events import RoleCreated
from app.modules.authentication.domain.exceptions import DuplicateRoleNameError
from tests.unit.modules.authentication.application.fakes import FakeRoleRepository, FakeUnitOfWork


@pytest.fixture
def role_repository() -> FakeRoleRepository:
    return FakeRoleRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def use_case(role_repository: FakeRoleRepository, unit_of_work: FakeUnitOfWork) -> CreateRole:
    return CreateRole(role_repository=role_repository, unit_of_work=unit_of_work)


class TestCreateRole:
    async def test_creates_an_org_scoped_role(
        self,
        use_case: CreateRole,
        role_repository: FakeRoleRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        org_id = uuid4()

        output = await use_case.execute(
            CreateRoleInput(organization_id=org_id, name="Front Desk", description="Reception")
        )

        stored = await role_repository.get_by_id(output.role_id)
        assert stored is not None
        assert stored.name == "Front Desk"
        assert stored.organization_id == org_id
        assert unit_of_work.committed is True

    async def test_commits_and_publishes_role_created_event(
        self, use_case: CreateRole, unit_of_work: FakeUnitOfWork
    ) -> None:
        await use_case.execute(CreateRoleInput(organization_id=uuid4(), name="Billing"))

        assert any(isinstance(e, RoleCreated) for e in unit_of_work.published_events)

    async def test_duplicate_org_role_name_is_rejected(self, use_case: CreateRole) -> None:
        org_id = uuid4()
        await use_case.execute(CreateRoleInput(organization_id=org_id, name="Nurse"))

        with pytest.raises(DuplicateRoleNameError):
            await use_case.execute(CreateRoleInput(organization_id=org_id, name="Nurse"))

    async def test_same_name_allowed_in_different_organizations(self, use_case: CreateRole) -> None:
        await use_case.execute(CreateRoleInput(organization_id=uuid4(), name="Nurse"))
        # A different organization reusing the same role name is not a duplicate.
        output = await use_case.execute(CreateRoleInput(organization_id=uuid4(), name="Nurse"))
        assert output.name == "Nurse"

    async def test_duplicate_system_role_name_is_rejected(self, use_case: CreateRole) -> None:
        await use_case.execute(
            CreateRoleInput(organization_id=None, name="Doctor", is_system_role=True)
        )
        with pytest.raises(DuplicateRoleNameError):
            await use_case.execute(
                CreateRoleInput(organization_id=None, name="Doctor", is_system_role=True)
            )
