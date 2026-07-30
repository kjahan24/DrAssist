"""Unit tests for the `AssignRoleToUser` use case."""

from uuid import uuid4

import pytest

from app.modules.authentication.application.dto import AssignRoleToUserInput
from app.modules.authentication.application.use_cases.assign_role_to_user import AssignRoleToUser
from app.modules.authentication.domain.entities import Role, User
from app.modules.authentication.domain.events import UserRoleAssigned
from app.modules.authentication.domain.exceptions import (
    InactiveRoleError,
    RoleNotFoundError,
    RoleOrganizationMismatchError,
    UserNotFoundError,
)
from app.modules.authentication.domain.value_objects import HashedPassword
from app.shared.domain.common_value_objects import EmailAddress
from tests.unit.modules.authentication.application.fakes import (
    FakeRoleRepository,
    FakeUnitOfWork,
    FakeUserRepository,
)

VALID_HASH = "$2b$12$" + "a" * 53


@pytest.fixture
def user_repository() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def role_repository() -> FakeRoleRepository:
    return FakeRoleRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def use_case(
    user_repository: FakeUserRepository,
    role_repository: FakeRoleRepository,
    unit_of_work: FakeUnitOfWork,
) -> AssignRoleToUser:
    return AssignRoleToUser(
        user_repository=user_repository, role_repository=role_repository, unit_of_work=unit_of_work
    )


class TestAssignRoleToUser:
    async def test_assigns_the_role_and_makes_it_visible_via_list_for_user(
        self,
        use_case: AssignRoleToUser,
        user_repository: FakeUserRepository,
        role_repository: FakeRoleRepository,
    ) -> None:
        org_id = uuid4()
        user = User.register(
            organization_id=org_id,
            email=EmailAddress("nurse@example.com"),
            password_hash=HashedPassword(VALID_HASH),
            first_name="Nora",
            last_name="Nurse",
        )
        await user_repository.add(user)
        role = Role.create(organization_id=org_id, name="Nurse")
        await role_repository.add(role)

        await use_case.execute(
            AssignRoleToUserInput(organization_id=org_id, user_id=user.id, role_id=role.id)
        )

        assigned_roles = await role_repository.list_for_user(user.id)
        assert [r.id for r in assigned_roles] == [role.id]

    async def test_publishes_user_role_assigned_event(
        self,
        use_case: AssignRoleToUser,
        user_repository: FakeUserRepository,
        role_repository: FakeRoleRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        org_id = uuid4()
        user = User.register(
            organization_id=org_id,
            email=EmailAddress("nurse2@example.com"),
            password_hash=HashedPassword(VALID_HASH),
            first_name="Nora",
            last_name="Nurse",
        )
        await user_repository.add(user)
        role = Role.create(organization_id=org_id, name="Nurse")
        await role_repository.add(role)
        granted_by = uuid4()

        await use_case.execute(
            AssignRoleToUserInput(
                organization_id=org_id, user_id=user.id, role_id=role.id, granted_by=granted_by
            )
        )

        events = [e for e in unit_of_work.published_events if isinstance(e, UserRoleAssigned)]
        assert len(events) == 1
        assert events[0].granted_by == granted_by

    async def test_unknown_user_raises(
        self, use_case: AssignRoleToUser, role_repository: FakeRoleRepository
    ) -> None:
        org_id = uuid4()
        role = Role.create(organization_id=org_id, name="Nurse")
        await role_repository.add(role)

        with pytest.raises(UserNotFoundError):
            await use_case.execute(
                AssignRoleToUserInput(organization_id=org_id, user_id=uuid4(), role_id=role.id)
            )

    async def test_user_from_a_different_organization_is_treated_as_not_found(
        self,
        use_case: AssignRoleToUser,
        user_repository: FakeUserRepository,
        role_repository: FakeRoleRepository,
    ) -> None:
        user = User.register(
            organization_id=uuid4(),
            email=EmailAddress("other-org@example.com"),
            password_hash=HashedPassword(VALID_HASH),
            first_name="Other",
            last_name="User",
        )
        await user_repository.add(user)
        different_org_id = uuid4()
        role = Role.create(organization_id=different_org_id, name="Nurse")
        await role_repository.add(role)

        with pytest.raises(UserNotFoundError):
            await use_case.execute(
                AssignRoleToUserInput(
                    organization_id=different_org_id, user_id=user.id, role_id=role.id
                )
            )

    async def test_unknown_role_raises(
        self, use_case: AssignRoleToUser, user_repository: FakeUserRepository
    ) -> None:
        org_id = uuid4()
        user = User.register(
            organization_id=org_id,
            email=EmailAddress("nurse3@example.com"),
            password_hash=HashedPassword(VALID_HASH),
            first_name="Nora",
            last_name="Nurse",
        )
        await user_repository.add(user)

        with pytest.raises(RoleNotFoundError):
            await use_case.execute(
                AssignRoleToUserInput(organization_id=org_id, user_id=user.id, role_id=uuid4())
            )

    async def test_role_from_a_different_organization_raises(
        self,
        use_case: AssignRoleToUser,
        user_repository: FakeUserRepository,
        role_repository: FakeRoleRepository,
    ) -> None:
        org_id = uuid4()
        user = User.register(
            organization_id=org_id,
            email=EmailAddress("nurse4@example.com"),
            password_hash=HashedPassword(VALID_HASH),
            first_name="Nora",
            last_name="Nurse",
        )
        await user_repository.add(user)
        role = Role.create(organization_id=uuid4(), name="Nurse")
        await role_repository.add(role)

        with pytest.raises(RoleOrganizationMismatchError):
            await use_case.execute(
                AssignRoleToUserInput(organization_id=org_id, user_id=user.id, role_id=role.id)
            )

    async def test_system_role_is_assignable_to_any_organization(
        self,
        use_case: AssignRoleToUser,
        user_repository: FakeUserRepository,
        role_repository: FakeRoleRepository,
    ) -> None:
        org_id = uuid4()
        user = User.register(
            organization_id=org_id,
            email=EmailAddress("doctor@example.com"),
            password_hash=HashedPassword(VALID_HASH),
            first_name="Dana",
            last_name="Doctor",
        )
        await user_repository.add(user)
        role = Role.create(organization_id=None, name="Doctor", is_system_role=True)
        await role_repository.add(role)

        await use_case.execute(
            AssignRoleToUserInput(organization_id=org_id, user_id=user.id, role_id=role.id)
        )

        assigned_roles = await role_repository.list_for_user(user.id)
        assert [r.id for r in assigned_roles] == [role.id]

    async def test_inactive_role_raises(
        self,
        use_case: AssignRoleToUser,
        user_repository: FakeUserRepository,
        role_repository: FakeRoleRepository,
    ) -> None:
        org_id = uuid4()
        user = User.register(
            organization_id=org_id,
            email=EmailAddress("nurse5@example.com"),
            password_hash=HashedPassword(VALID_HASH),
            first_name="Nora",
            last_name="Nurse",
        )
        await user_repository.add(user)
        role = Role.create(organization_id=org_id, name="Nurse")
        role.deactivate()
        await role_repository.add(role)

        with pytest.raises(InactiveRoleError):
            await use_case.execute(
                AssignRoleToUserInput(organization_id=org_id, user_id=user.id, role_id=role.id)
            )
