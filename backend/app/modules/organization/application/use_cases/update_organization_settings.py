"""`UpdateOrganizationSettings` — partial update of an organization's
existing settings. There is deliberately no "create" counterpart here; see
`create_organization.py`."""

from app.modules.organization.application.dto import (
    UpdateOrganizationSettingsInput,
    UpdateOrganizationSettingsOutput,
)
from app.modules.organization.domain.exceptions import OrganizationSettingsNotFoundError
from app.modules.organization.domain.repositories import OrganizationSettingsRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class UpdateOrganizationSettings(
    UseCase[UpdateOrganizationSettingsInput, UpdateOrganizationSettingsOutput]
):
    def __init__(
        self,
        *,
        organization_settings_repository: OrganizationSettingsRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._settings = organization_settings_repository
        self._uow = unit_of_work

    async def execute(
        self, input_dto: UpdateOrganizationSettingsInput
    ) -> UpdateOrganizationSettingsOutput:
        settings = await self._settings.get_by_organization_id(input_dto.organization_id)
        if settings is None:
            raise OrganizationSettingsNotFoundError(input_dto.organization_id)

        settings.update(
            working_hours=input_dto.working_hours,
            appointment_duration_minutes=input_dto.appointment_duration_minutes,
            default_timezone=input_dto.default_timezone,
            default_language=input_dto.default_language,
            default_currency=input_dto.default_currency,
            feature_flags=input_dto.feature_flags,
            ai_settings=input_dto.ai_settings,
            notification_settings=input_dto.notification_settings,
        )

        await self._settings.add(settings)
        self._uow.collect_events(settings.pull_events())
        await self._uow.commit()

        return UpdateOrganizationSettingsOutput(
            organization_id=settings.organization_id,
            settings_id=settings.id,
            appointment_duration_minutes=settings.appointment_duration_minutes,
            default_timezone=settings.default_timezone,
        )
