"""Unit tests for `ScheduleConsistencyService` — "FK validation" and
"Organization consistency" for `doctor_id`."""

from uuid import uuid4

import pytest

from app.modules.schedule.application.services.schedule_consistency_service import (
    ScheduleConsistencyService,
)
from app.modules.schedule.domain.exceptions import DoctorNotFoundError
from tests.unit.modules.schedule.application.fakes import (
    FakeDoctorQueryPort,
    make_doctor_summary,
)


class TestResolveOrganizationForDoctor:
    async def test_returns_the_doctors_own_organization_id(self) -> None:
        organization_id = uuid4()
        doctor_id = uuid4()
        port = FakeDoctorQueryPort(
            existing_doctors={
                doctor_id: make_doctor_summary(doctor_id=doctor_id, organization_id=organization_id)
            }
        )
        service = ScheduleConsistencyService(doctor_query_port=port)

        result = await service.resolve_organization_for_doctor(doctor_id)

        assert result == organization_id

    async def test_unknown_doctor_raises(self) -> None:
        service = ScheduleConsistencyService(doctor_query_port=FakeDoctorQueryPort())
        with pytest.raises(DoctorNotFoundError):
            await service.resolve_organization_for_doctor(uuid4())
