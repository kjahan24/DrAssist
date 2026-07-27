"""Unit tests for `RbacPermissionService` — effective-permission resolution
across every role a user holds."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.authentication.application.services.permission_service import (
    RbacPermissionService,
)
from app.modules.authentication.domain.entities import Permission, Role
from app.modules.authentication.domain.value_objects import PermissionCode
from tests.unit.modules.authentication.application.fakes import (
    FakePermissionRepository,
    FakeRoleRepository,
)


@pytest.fixture
def role_repository() -> FakeRoleRepository:
    return FakeRoleRepository()


@pytest.fixture
def permission_repository() -> FakePermissionRepository:
    return FakePermissionRepository()


@pytest.fixture
def service(
    role_repository: FakeRoleRepository, permission_repository: FakePermissionRepository
) -> RbacPermissionService:
    return RbacPermissionService(
        role_repository=role_repository, permission_repository=permission_repository
    )


async def _seed_role_with_permission(
    role_repository: FakeRoleRepository,
    permission_repository: FakePermissionRepository,
    *,
    organization_id,
    user_id,
    role_name: str,
    permission_code: str,
) -> None:
    role = Role.create(organization_id=organization_id, name=role_name)
    await role_repository.add(role)
    await role_repository.assign_to_user(
        organization_id=organization_id,
        user_id=user_id,
        role_id=role.id,
        granted_by=None,
        granted_at=datetime.now(UTC),
    )
    permission = Permission.create(
        code=PermissionCode(permission_code), module=permission_code.split(".")[0], description=""
    )
    await permission_repository.add(permission)
    permission_repository.seed_role_permission(role.id, permission.id)


class TestGetEffectivePermissionCodes:
    async def test_user_with_no_roles_has_no_permissions(
        self, service: RbacPermissionService
    ) -> None:
        assert await service.get_effective_permission_codes(uuid4()) == frozenset()

    async def test_union_of_permissions_across_multiple_roles(
        self,
        service: RbacPermissionService,
        role_repository: FakeRoleRepository,
        permission_repository: FakePermissionRepository,
    ) -> None:
        org_id, user_id = uuid4(), uuid4()
        await _seed_role_with_permission(
            role_repository,
            permission_repository,
            organization_id=org_id,
            user_id=user_id,
            role_name="Nurse",
            permission_code="patients.read",
        )
        await _seed_role_with_permission(
            role_repository,
            permission_repository,
            organization_id=org_id,
            user_id=user_id,
            role_name="Billing",
            permission_code="invoices.write",
        )

        codes = await service.get_effective_permission_codes(user_id)

        assert codes == frozenset({"patients.read", "invoices.write"})

    async def test_permissions_are_scoped_to_the_specific_user(
        self,
        service: RbacPermissionService,
        role_repository: FakeRoleRepository,
        permission_repository: FakePermissionRepository,
    ) -> None:
        org_id = uuid4()
        user_a, user_b = uuid4(), uuid4()
        await _seed_role_with_permission(
            role_repository,
            permission_repository,
            organization_id=org_id,
            user_id=user_a,
            role_name="Nurse",
            permission_code="patients.read",
        )

        assert await service.get_effective_permission_codes(user_b) == frozenset()


class TestHasPermission:
    async def test_true_when_permission_is_held(
        self,
        service: RbacPermissionService,
        role_repository: FakeRoleRepository,
        permission_repository: FakePermissionRepository,
    ) -> None:
        org_id, user_id = uuid4(), uuid4()
        await _seed_role_with_permission(
            role_repository,
            permission_repository,
            organization_id=org_id,
            user_id=user_id,
            role_name="Nurse",
            permission_code="patients.read",
        )

        assert await service.has_permission(user_id, "patients.read") is True

    async def test_false_when_permission_is_not_held(self, service: RbacPermissionService) -> None:
        assert await service.has_permission(uuid4(), "patients.read") is False
