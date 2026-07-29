"""Unit tests for the `CreateClinicalNote` use case, using in-memory
fakes for both this module's own repository and the Visit/Doctor
modules' public ports."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.modules.clinical_notes.application.dto import CreateClinicalNoteInput
from app.modules.clinical_notes.application.use_cases.create_clinical_note import (
    CreateClinicalNote,
)
from app.modules.clinical_notes.domain.enums import ClinicalNoteType
from app.modules.clinical_notes.domain.events import ClinicalNoteCreated
from app.modules.clinical_notes.domain.exceptions import (
    DuplicateNoteNumberError,
    VisitPatientMismatchError,
)
from app.modules.doctor.domain.exceptions import DoctorNotFoundError
from app.modules.visit.domain.exceptions import PatientVisitNotFoundError
from tests.unit.modules.clinical_notes.application.fakes import (
    FakeClinicalNoteRepository,
    FakeDoctorQueryPort,
    FakeUnitOfWork,
    FakeVisitQueryPort,
)


def _make_input(**overrides: object) -> CreateClinicalNoteInput:
    defaults: dict[str, object] = {
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "note_number": "CN-0001",
        "note_type": ClinicalNoteType.INITIAL,
        "encounter_datetime": datetime(2026, 1, 1, 9, 0),
    }
    defaults.update(overrides)
    return CreateClinicalNoteInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def clinical_note_repository() -> FakeClinicalNoteRepository:
    return FakeClinicalNoteRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    clinical_note_repository: FakeClinicalNoteRepository,
    unit_of_work: FakeUnitOfWork,
    *,
    existing_visits: dict[object, object] | None = None,
    existing_doctors: dict[object, object] | None = None,
) -> CreateClinicalNote:
    return CreateClinicalNote(
        clinical_note_repository=clinical_note_repository,
        visit_query_port=FakeVisitQueryPort(existing_visits=existing_visits),  # type: ignore[arg-type]
        doctor_query_port=FakeDoctorQueryPort(existing_doctors=existing_doctors),  # type: ignore[arg-type]
        unit_of_work=unit_of_work,
    )


class TestCreateClinicalNote:
    async def test_creates_a_note_for_an_existing_visit_with_matching_patient(
        self,
        clinical_note_repository: FakeClinicalNoteRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        patient_id = uuid4()
        organization_id = uuid4()
        doctor_id = uuid4()
        use_case = _use_case(
            clinical_note_repository,
            unit_of_work,
            existing_visits={visit_id: (organization_id, patient_id)},
            existing_doctors={doctor_id: organization_id},
        )

        output = await use_case.execute(
            _make_input(visit_id=visit_id, patient_id=patient_id, doctor_id=doctor_id)
        )

        stored = await clinical_note_repository.get_by_id(output.clinical_note_id)
        assert stored is not None
        assert stored.organization_id == organization_id
        assert unit_of_work.committed is True
        assert any(isinstance(e, ClinicalNoteCreated) for e in unit_of_work.published_events)

    async def test_unknown_visit_raises(
        self,
        clinical_note_repository: FakeClinicalNoteRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = _use_case(clinical_note_repository, unit_of_work)

        with pytest.raises(PatientVisitNotFoundError):
            await use_case.execute(_make_input(visit_id=uuid4()))

    async def test_patient_id_not_matching_visits_patient_raises(
        self,
        clinical_note_repository: FakeClinicalNoteRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        use_case = _use_case(
            clinical_note_repository,
            unit_of_work,
            existing_visits={visit_id: (uuid4(), uuid4())},
        )

        with pytest.raises(VisitPatientMismatchError):
            await use_case.execute(_make_input(visit_id=visit_id, patient_id=uuid4()))

    async def test_doctor_id_with_unknown_doctor_raises(
        self,
        clinical_note_repository: FakeClinicalNoteRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        patient_id = uuid4()
        use_case = _use_case(
            clinical_note_repository,
            unit_of_work,
            existing_visits={visit_id: (uuid4(), patient_id)},
        )

        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(
                _make_input(visit_id=visit_id, patient_id=patient_id, doctor_id=uuid4())
            )

    async def test_doctor_from_a_different_organization_raises(
        self,
        clinical_note_repository: FakeClinicalNoteRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        patient_id = uuid4()
        doctor_id = uuid4()
        use_case = _use_case(
            clinical_note_repository,
            unit_of_work,
            existing_visits={visit_id: (uuid4(), patient_id)},
            existing_doctors={doctor_id: uuid4()},
        )

        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(
                _make_input(visit_id=visit_id, patient_id=patient_id, doctor_id=doctor_id)
            )

    async def test_doctor_in_the_same_organization_is_accepted(
        self,
        clinical_note_repository: FakeClinicalNoteRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        patient_id = uuid4()
        doctor_id = uuid4()
        organization_id = uuid4()
        use_case = _use_case(
            clinical_note_repository,
            unit_of_work,
            existing_visits={visit_id: (organization_id, patient_id)},
            existing_doctors={doctor_id: organization_id},
        )

        output = await use_case.execute(
            _make_input(visit_id=visit_id, patient_id=patient_id, doctor_id=doctor_id)
        )

        stored = await clinical_note_repository.get_by_id(output.clinical_note_id)
        assert stored is not None
        assert stored.doctor_id == doctor_id

    async def test_duplicate_note_number_is_rejected(
        self,
        clinical_note_repository: FakeClinicalNoteRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_a = uuid4()
        visit_b = uuid4()
        patient_a = uuid4()
        patient_b = uuid4()
        org_a = uuid4()
        org_b = uuid4()
        doctor_a = uuid4()
        doctor_b = uuid4()
        use_case = _use_case(
            clinical_note_repository,
            unit_of_work,
            existing_visits={
                visit_a: (org_a, patient_a),
                visit_b: (org_b, patient_b),
            },
            existing_doctors={doctor_a: org_a, doctor_b: org_b},
        )

        await use_case.execute(
            _make_input(
                visit_id=visit_a,
                patient_id=patient_a,
                doctor_id=doctor_a,
                note_number="CN-SHARED",
            )
        )

        with pytest.raises(DuplicateNoteNumberError):
            await use_case.execute(
                _make_input(
                    visit_id=visit_b,
                    patient_id=patient_b,
                    doctor_id=doctor_b,
                    note_number="CN-SHARED",
                )
            )

    async def test_distinct_note_numbers_on_different_visits_are_allowed(
        self,
        clinical_note_repository: FakeClinicalNoteRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_a = uuid4()
        visit_b = uuid4()
        patient_a = uuid4()
        patient_b = uuid4()
        org_a = uuid4()
        org_b = uuid4()
        doctor_a = uuid4()
        doctor_b = uuid4()
        use_case = _use_case(
            clinical_note_repository,
            unit_of_work,
            existing_visits={
                visit_a: (org_a, patient_a),
                visit_b: (org_b, patient_b),
            },
            existing_doctors={doctor_a: org_a, doctor_b: org_b},
        )

        await use_case.execute(
            _make_input(
                visit_id=visit_a, patient_id=patient_a, doctor_id=doctor_a, note_number="CN-0001"
            )
        )
        output_b = await use_case.execute(
            _make_input(
                visit_id=visit_b, patient_id=patient_b, doctor_id=doctor_b, note_number="CN-0002"
            )
        )

        stored_b = await clinical_note_repository.get_by_id(output_b.clinical_note_id)
        assert stored_b is not None
        assert stored_b.visit_id == visit_b
