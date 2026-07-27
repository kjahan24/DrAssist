"""`CreateDepartment` — a department always belongs to exactly one
organization; this use case is the only way one is created, and it always
requires a real, existing organization."""

from app.modules.organization.application.dto import CreateDepartmentInput, CreateDepartmentOutput
from app.modules.organization.domain.entities import Department
from app.modules.organization.domain.exceptions import OrganizationNotFoundError
from app.modules.organization.domain.repositories import (
    DepartmentRepository,
    OrganizationRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreateDepartment(UseCase[CreateDepartmentInput, CreateDepartmentOutput]):
    def __init__(
        self,
        *,
        department_repository: DepartmentRepository,
        organization_repository: OrganizationRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._departments = department_repository
        self._organizations = organization_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: CreateDepartmentInput) -> CreateDepartmentOutput:
        organization = await self._organizations.get_by_id(input_dto.organization_id)
        if organization is None:
            raise OrganizationNotFoundError(input_dto.organization_id)

        department = Department.create(
            organization_id=organization.id,
            name=input_dto.name,
            description=input_dto.description,
        )
        await self._departments.add(department)
        self._uow.collect_events(department.pull_events())
        await self._uow.commit()

        return CreateDepartmentOutput(
            department_id=department.id,
            organization_id=department.organization_id,
            name=department.name,
            status=department.status,
        )
