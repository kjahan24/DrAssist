"""Unit tests for the `CreatePermission` use case, using an in-memory
fake for this module's own `PermissionRepository`."""

import pytest

from app.modules.authentication.application.dto import CreatePermissionInput
from app.modules.authentication.application.use_cases.create_permission import CreatePermission
from app.modules.authentication.domain.events import PermissionCreated
from app.modules.authentication.domain.exceptions import DuplicatePermissionCodeError
from tests.unit.modules.authentication.application.fakes import (
    FakePermissionRepository,
    FakeUnitOfWork,
)


@pytest.fixture
def permission_repository() -> FakePermissionRepository:
    return FakePermissionRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def use_case(
    permission_repository: FakePermissionRepository, unit_of_work: FakeUnitOfWork
) -> CreatePermission:
    return CreatePermission(permission_repository=permission_repository, unit_of_work=unit_of_work)


class TestCreatePermission:
    async def test_creates_a_permission_with_derived_resource_and_action(
        self,
        use_case: CreatePermission,
        permission_repository: FakePermissionRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        output = await use_case.execute(
            CreatePermissionInput(code="patients.read", name="Read patients")
        )

        assert output.resource == "patients"
        assert output.action == "read"
        stored = await permission_repository.get_by_code("patients.read")
        assert stored is not None
        assert stored.name == "Read patients"
        assert unit_of_work.committed is True
        assert any(isinstance(e, PermissionCreated) for e in unit_of_work.published_events)

    async def test_duplicate_code_is_rejected(self, use_case: CreatePermission) -> None:
        await use_case.execute(CreatePermissionInput(code="patients.read", name="Read patients"))

        with pytest.raises(DuplicatePermissionCodeError):
            await use_case.execute(
                CreatePermissionInput(code="patients.read", name="Read patients again")
            )
