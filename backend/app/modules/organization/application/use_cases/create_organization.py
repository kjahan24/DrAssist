"""`CreateOrganization` — provisions a new tenant *and* its default
`OrganizationSettings` in one transaction.

Creating both together, with no standalone "create settings" use case, is
what makes the one-to-one `Organization` <-> `OrganizationSettings`
invariant impossible to violate rather than something that has to be
checked for — see `OrganizationSettings.create_default`.
"""

from app.modules.organization.application.dto import (
    CreateOrganizationInput,
    CreateOrganizationOutput,
)
from app.modules.organization.domain.entities import Organization, OrganizationSettings
from app.modules.organization.domain.exceptions import DuplicateOrganizationCodeError
from app.modules.organization.domain.repositories import (
    OrganizationRepository,
    OrganizationSettingsRepository,
)
from app.modules.organization.domain.value_objects import OrganizationCode
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase
from app.shared.domain.common_value_objects import EmailAddress


class CreateOrganization(UseCase[CreateOrganizationInput, CreateOrganizationOutput]):
    def __init__(
        self,
        *,
        organization_repository: OrganizationRepository,
        organization_settings_repository: OrganizationSettingsRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._organizations = organization_repository
        self._settings = organization_settings_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: CreateOrganizationInput) -> CreateOrganizationOutput:
        code = OrganizationCode(input_dto.organization_code)

        existing = await self._organizations.get_by_code(str(code))
        if existing is not None:
            raise DuplicateOrganizationCodeError(str(code))

        organization = Organization.create(
            organization_code=code,
            name=input_dto.name,
            type=input_dto.type,
            legal_name=input_dto.legal_name,
            email=EmailAddress(input_dto.email) if input_dto.email else None,
            phone=input_dto.phone,
            website=input_dto.website,
            logo_url=input_dto.logo_url,
            tax_number=input_dto.tax_number,
            registration_number=input_dto.registration_number,
            address=input_dto.address,
            city=input_dto.city,
            state=input_dto.state,
            country=input_dto.country,
            postal_code=input_dto.postal_code,
            timezone=input_dto.timezone,
            currency=input_dto.currency,
            language=input_dto.language,
        )
        settings = OrganizationSettings.create_default(organization_id=organization.id)

        await self._organizations.add(organization)
        await self._settings.add(settings)

        self._uow.collect_events(organization.pull_events())
        self._uow.collect_events(settings.pull_events())
        await self._uow.commit()

        return CreateOrganizationOutput(
            organization_id=organization.id,
            organization_code=str(organization.organization_code),
            name=organization.name,
            type=organization.type,
            settings_id=settings.id,
        )
