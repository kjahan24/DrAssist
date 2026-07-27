"""Unit tests for the `CreateDepartment` use case."""

from uuid import uuid4

import pytest

from app.modules.organization.application.dto import CreateDepartmentInput
from app.modules.organization.application.use_cases.create_department import CreateDepartment
from app.modules.organization.domain.entities import Organization
from app.modules.organization.domain.enums import OrganizationType
from app.modules.organization.domain.events import DepartmentCreated
from app.modules.organization.domain.exceptions import OrganizationNotFoundError
from app.modules.organization.domain.value_objects import OrganizationCode
from tests.unit.modules.organization.application.fakes import (
    FakeDepartmentRepository,
    FakeOrganizationRepository,
    FakeUnitOfWork,
)


@pytest.fixture
def department_repository() -> FakeDepartmentRepository:
    return FakeDepartmentRepository()


@pytest.fixture
def organization_repository() -> FakeOrganizationRepository:
    return FakeOrganizationRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def use_case(
    department_repository: FakeDepartmentRepository,
    organization_repository: FakeOrganizationRepository,
    unit_of_work: FakeUnitOfWork,
) -> CreateDepartment:
    return CreateDepartment(
        department_repository=department_repository,
        organization_repository=organization_repository,
        unit_of_work=unit_of_work,
    )


class TestCreateDepartment:
    async def test_creates_department_for_existing_organization(
        self,
        use_case: CreateDepartment,
        organization_repository: FakeOrganizationRepository,
        department_repository: FakeDepartmentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        organization = Organization.create(
            organization_code=OrganizationCode("ACME"),
            name="Acme Clinic",
            type=OrganizationType.CLINIC,
        )
        await organization_repository.add(organization)

        output = await use_case.execute(
            CreateDepartmentInput(organization_id=organization.id, name="Cardiology")
        )

        stored = await department_repository.get_by_id(output.department_id)
        assert stored is not None
        assert stored.organization_id == organization.id
        assert unit_of_work.committed is True
        assert any(isinstance(e, DepartmentCreated) for e in unit_of_work.published_events)

    async def test_department_belongs_to_exactly_one_organization(
        self,
        use_case: CreateDepartment,
        organization_repository: FakeOrganizationRepository,
        department_repository: FakeDepartmentRepository,
    ) -> None:
        org_a = Organization.create(
            organization_code=OrganizationCode("ORG-A"), name="Org A", type=OrganizationType.CLINIC
        )
        org_b = Organization.create(
            organization_code=OrganizationCode("ORG-B"), name="Org B", type=OrganizationType.CLINIC
        )
        await organization_repository.add(org_a)
        await organization_repository.add(org_b)

        output = await use_case.execute(
            CreateDepartmentInput(organization_id=org_a.id, name="Radiology")
        )

        departments_for_a = await department_repository.list_by_organization(org_a.id)
        departments_for_b = await department_repository.list_by_organization(org_b.id)
        assert [d.id for d in departments_for_a] == [output.department_id]
        assert departments_for_b == []

    async def test_unknown_organization_raises(self, use_case: CreateDepartment) -> None:
        with pytest.raises(OrganizationNotFoundError):
            await use_case.execute(
                CreateDepartmentInput(organization_id=uuid4(), name="Cardiology")
            )
