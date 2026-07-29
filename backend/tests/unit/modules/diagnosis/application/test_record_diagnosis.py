"""Unit tests for the `RecordVisitDiagnosis` use case, using in-memory
fakes for both this module's own repository and the Visit/Doctor
modules' public ports."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.modules.diagnosis.application.dto import RecordVisitDiagnosisInput
from app.modules.diagnosis.application.use_cases.record_diagnosis import RecordVisitDiagnosis
from app.modules.diagnosis.domain.enums import DiagnosisType
from app.modules.diagnosis.domain.events import VisitDiagnosisRecorded
from app.modules.diagnosis.domain.exceptions import (
    DuplicatePrimaryDiagnosisError,
    DuplicateSequenceNumberError,
)
from app.modules.doctor.domain.exceptions import DoctorNotFoundError
from app.modules.visit.domain.exceptions import PatientVisitNotFoundError
from tests.unit.modules.diagnosis.application.fakes import (
    FakeDoctorQueryPort,
    FakeUnitOfWork,
    FakeVisitDiagnosisRepository,
    FakeVisitQueryPort,
)


def _make_input(**overrides: object) -> RecordVisitDiagnosisInput:
    defaults: dict[str, object] = {
        "visit_id": uuid4(),
        "sequence_number": 1,
        "diagnosis_name": "Type 2 diabetes",
        "diagnosis_type": DiagnosisType.PRIMARY,
        "diagnosed_at": datetime(2026, 1, 1, 9, 0),
    }
    defaults.update(overrides)
    return RecordVisitDiagnosisInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def diagnosis_repository() -> FakeVisitDiagnosisRepository:
    return FakeVisitDiagnosisRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    diagnosis_repository: FakeVisitDiagnosisRepository,
    unit_of_work: FakeUnitOfWork,
    *,
    existing_visits: dict[object, object] | None = None,
    existing_doctors: dict[object, object] | None = None,
) -> RecordVisitDiagnosis:
    return RecordVisitDiagnosis(
        diagnosis_repository=diagnosis_repository,
        visit_query_port=FakeVisitQueryPort(existing_visits=existing_visits),  # type: ignore[arg-type]
        doctor_query_port=FakeDoctorQueryPort(existing_doctors=existing_doctors),  # type: ignore[arg-type]
        unit_of_work=unit_of_work,
    )


class TestRecordVisitDiagnosis:
    async def test_records_a_diagnosis_for_an_existing_visit(
        self,
        diagnosis_repository: FakeVisitDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        organization_id = uuid4()
        use_case = _use_case(
            diagnosis_repository, unit_of_work, existing_visits={visit_id: organization_id}
        )

        output = await use_case.execute(_make_input(visit_id=visit_id))

        stored = await diagnosis_repository.get_by_id(output.diagnosis_id)
        assert stored is not None
        assert stored.organization_id == organization_id
        assert output.sequence_number == 1
        assert unit_of_work.committed is True
        assert any(isinstance(e, VisitDiagnosisRecorded) for e in unit_of_work.published_events)

    async def test_unknown_visit_raises(
        self,
        diagnosis_repository: FakeVisitDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = _use_case(diagnosis_repository, unit_of_work)

        with pytest.raises(PatientVisitNotFoundError):
            await use_case.execute(_make_input(visit_id=uuid4()))

    async def test_diagnosed_by_with_unknown_doctor_raises(
        self,
        diagnosis_repository: FakeVisitDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        use_case = _use_case(
            diagnosis_repository, unit_of_work, existing_visits={visit_id: uuid4()}
        )

        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(_make_input(visit_id=visit_id, diagnosed_by=uuid4()))

    async def test_diagnosed_by_doctor_from_a_different_organization_raises(
        self,
        diagnosis_repository: FakeVisitDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        doctor_id = uuid4()
        visit_organization_id = uuid4()
        doctor_organization_id = uuid4()
        use_case = _use_case(
            diagnosis_repository,
            unit_of_work,
            existing_visits={visit_id: visit_organization_id},
            existing_doctors={doctor_id: doctor_organization_id},
        )

        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(_make_input(visit_id=visit_id, diagnosed_by=doctor_id))

    async def test_diagnosed_by_doctor_in_the_same_organization_is_accepted(
        self,
        diagnosis_repository: FakeVisitDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        doctor_id = uuid4()
        organization_id = uuid4()
        use_case = _use_case(
            diagnosis_repository,
            unit_of_work,
            existing_visits={visit_id: organization_id},
            existing_doctors={doctor_id: organization_id},
        )

        output = await use_case.execute(_make_input(visit_id=visit_id, diagnosed_by=doctor_id))

        stored = await diagnosis_repository.get_by_id(output.diagnosis_id)
        assert stored is not None
        assert stored.diagnosed_by == doctor_id

    async def test_duplicate_sequence_number_within_the_same_visit_is_rejected(
        self,
        diagnosis_repository: FakeVisitDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        use_case = _use_case(
            diagnosis_repository, unit_of_work, existing_visits={visit_id: uuid4()}
        )

        await use_case.execute(
            _make_input(visit_id=visit_id, sequence_number=1, diagnosis_type=DiagnosisType.PRIMARY)
        )

        with pytest.raises(DuplicateSequenceNumberError):
            await use_case.execute(
                _make_input(
                    visit_id=visit_id, sequence_number=1, diagnosis_type=DiagnosisType.SECONDARY
                )
            )

    async def test_second_primary_diagnosis_for_the_same_visit_is_rejected(
        self,
        diagnosis_repository: FakeVisitDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        use_case = _use_case(
            diagnosis_repository, unit_of_work, existing_visits={visit_id: uuid4()}
        )

        await use_case.execute(
            _make_input(visit_id=visit_id, sequence_number=1, diagnosis_type=DiagnosisType.PRIMARY)
        )

        with pytest.raises(DuplicatePrimaryDiagnosisError):
            await use_case.execute(
                _make_input(
                    visit_id=visit_id, sequence_number=2, diagnosis_type=DiagnosisType.PRIMARY
                )
            )

    async def test_multiple_secondary_diagnoses_for_the_same_visit_are_allowed(
        self,
        diagnosis_repository: FakeVisitDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        use_case = _use_case(
            diagnosis_repository, unit_of_work, existing_visits={visit_id: uuid4()}
        )

        await use_case.execute(
            _make_input(
                visit_id=visit_id, sequence_number=1, diagnosis_type=DiagnosisType.SECONDARY
            )
        )
        output_2 = await use_case.execute(
            _make_input(
                visit_id=visit_id, sequence_number=2, diagnosis_type=DiagnosisType.SECONDARY
            )
        )

        stored = await diagnosis_repository.list_by_visit(visit_id)
        assert [d.sequence_number for d in stored] == [1, 2]
        assert output_2.diagnosis_type is DiagnosisType.SECONDARY

    async def test_primary_diagnosis_on_different_visits_is_allowed(
        self,
        diagnosis_repository: FakeVisitDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_a = uuid4()
        visit_b = uuid4()
        use_case = _use_case(
            diagnosis_repository,
            unit_of_work,
            existing_visits={visit_a: uuid4(), visit_b: uuid4()},
        )

        await use_case.execute(
            _make_input(visit_id=visit_a, sequence_number=1, diagnosis_type=DiagnosisType.PRIMARY)
        )
        output_b = await use_case.execute(
            _make_input(visit_id=visit_b, sequence_number=1, diagnosis_type=DiagnosisType.PRIMARY)
        )

        stored_b = await diagnosis_repository.get_by_id(output_b.diagnosis_id)
        assert stored_b is not None
        assert stored_b.visit_id == visit_b
