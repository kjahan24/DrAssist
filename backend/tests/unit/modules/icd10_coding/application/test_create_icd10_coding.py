"""Unit tests for the `CreateICD10Coding` use case, using in-memory fakes
for this module's own repository and the Clinical Notes/Differential
Diagnosis modules' public ports."""

from uuid import uuid4

import pytest

from app.modules.icd10_coding.application.dto import CreateICD10CodingInput
from app.modules.icd10_coding.application.use_cases.create_icd10_coding import (
    CreateICD10Coding,
)
from app.modules.icd10_coding.domain.enums import CodingSource, ReviewStatus
from app.modules.icd10_coding.domain.events import ICD10CodingCreated
from app.modules.icd10_coding.domain.exceptions import (
    ClinicalNoteNotFoundError,
    DifferentialDiagnosisClinicalNoteMismatchError,
    DifferentialDiagnosisNotFoundError,
    DuplicateICD10CodeError,
    DuplicatePrimaryCodeError,
)
from tests.unit.modules.icd10_coding.application.fakes import (
    FakeClinicalNoteQueryPort,
    FakeDifferentialDiagnosisQueryPort,
    FakeICD10CodingRepository,
    FakeUnitOfWork,
    make_clinical_note_summary,
    make_differential_diagnosis_summary,
)


def _make_input(**overrides: object) -> CreateICD10CodingInput:
    defaults: dict[str, object] = {
        "clinical_note_id": uuid4(),
        "icd10_code": "J18.9",
        "diagnosis_title": "Pneumonia, unspecified organism",
        "coding_source": CodingSource.AI,
    }
    defaults.update(overrides)
    return CreateICD10CodingInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def coding_repository() -> FakeICD10CodingRepository:
    return FakeICD10CodingRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    coding_repository: FakeICD10CodingRepository,
    unit_of_work: FakeUnitOfWork,
    clinical_note_query_port: FakeClinicalNoteQueryPort,
    differential_diagnosis_query_port: FakeDifferentialDiagnosisQueryPort | None = None,
) -> CreateICD10Coding:
    return CreateICD10Coding(
        icd10_coding_repository=coding_repository,
        clinical_note_query_port=clinical_note_query_port,
        differential_diagnosis_query_port=differential_diagnosis_query_port
        or FakeDifferentialDiagnosisQueryPort(),
        unit_of_work=unit_of_work,
    )


class TestCreateICD10Coding:
    async def test_creates_ai_generated_code_starting_pending(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        organization_id = uuid4()
        patient_id = uuid4()
        visit_id = uuid4()
        doctor_id = uuid4()
        summary = make_clinical_note_summary(
            clinical_note_id=clinical_note_id,
            organization_id=organization_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
        )
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(coding_repository, unit_of_work, port)

        output = await use_case.execute(_make_input(clinical_note_id=clinical_note_id))

        assert output.review_status is ReviewStatus.PENDING
        stored = await coding_repository.get_by_id(output.icd10_coding_id)
        assert stored is not None
        assert stored.organization_id == organization_id
        assert stored.patient_id == patient_id
        assert stored.visit_id == visit_id
        assert stored.doctor_id == doctor_id
        assert unit_of_work.committed is True
        assert any(isinstance(e, ICD10CodingCreated) for e in unit_of_work.published_events)

    async def test_creates_physician_generated_code_starting_reviewed(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(coding_repository, unit_of_work, port)

        output = await use_case.execute(
            _make_input(clinical_note_id=clinical_note_id, coding_source=CodingSource.PHYSICIAN)
        )

        assert output.review_status is ReviewStatus.REVIEWED

    async def test_unknown_clinical_note_raises(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        port = FakeClinicalNoteQueryPort()
        use_case = _use_case(coding_repository, unit_of_work, port)

        with pytest.raises(ClinicalNoteNotFoundError):
            await use_case.execute(_make_input(clinical_note_id=uuid4()))

    async def test_multiple_codes_for_the_same_clinical_note_are_allowed(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(coding_repository, unit_of_work, port)

        await use_case.execute(_make_input(clinical_note_id=clinical_note_id, icd10_code="J18.9"))
        output_b = await use_case.execute(
            _make_input(clinical_note_id=clinical_note_id, icd10_code="R05")
        )

        stored_b = await coding_repository.get_by_id(output_b.icd10_coding_id)
        assert stored_b is not None
        assert stored_b.clinical_note_id == clinical_note_id

    async def test_duplicate_icd10_code_within_the_same_clinical_note_raises(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(coding_repository, unit_of_work, port)
        await use_case.execute(_make_input(clinical_note_id=clinical_note_id, icd10_code="J18.9"))

        with pytest.raises(DuplicateICD10CodeError):
            await use_case.execute(
                _make_input(clinical_note_id=clinical_note_id, icd10_code="j18.9")
            )

    async def test_same_icd10_code_across_different_clinical_notes_is_allowed(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_a = uuid4()
        clinical_note_b = uuid4()
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_a: make_clinical_note_summary(clinical_note_id=clinical_note_a),
                clinical_note_b: make_clinical_note_summary(clinical_note_id=clinical_note_b),
            }
        )
        use_case = _use_case(coding_repository, unit_of_work, port)

        await use_case.execute(_make_input(clinical_note_id=clinical_note_a, icd10_code="J18.9"))
        output_b = await use_case.execute(
            _make_input(clinical_note_id=clinical_note_b, icd10_code="J18.9")
        )

        stored_b = await coding_repository.get_by_id(output_b.icd10_coding_id)
        assert stored_b is not None
        assert stored_b.icd10_code == "J18.9"

    async def test_marking_primary_when_no_sibling_is_primary_is_allowed(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(coding_repository, unit_of_work, port)

        output = await use_case.execute(
            _make_input(clinical_note_id=clinical_note_id, primary_code=True)
        )

        stored = await coding_repository.get_by_id(output.icd10_coding_id)
        assert stored is not None
        assert stored.primary_code is True

    async def test_marking_primary_when_a_sibling_is_already_primary_raises(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(coding_repository, unit_of_work, port)
        await use_case.execute(
            _make_input(clinical_note_id=clinical_note_id, icd10_code="J18.9", primary_code=True)
        )

        with pytest.raises(DuplicatePrimaryCodeError):
            await use_case.execute(
                _make_input(clinical_note_id=clinical_note_id, icd10_code="R05", primary_code=True)
            )

    async def test_valid_differential_diagnosis_link_is_accepted(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        differential_diagnosis_id = uuid4()
        note_port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        diagnosis_port = FakeDifferentialDiagnosisQueryPort(
            existing_records={
                differential_diagnosis_id: make_differential_diagnosis_summary(
                    differential_diagnosis_id=differential_diagnosis_id,
                    clinical_note_id=clinical_note_id,
                )
            }
        )
        use_case = _use_case(coding_repository, unit_of_work, note_port, diagnosis_port)

        output = await use_case.execute(
            _make_input(
                clinical_note_id=clinical_note_id,
                differential_diagnosis_id=differential_diagnosis_id,
            )
        )

        stored = await coding_repository.get_by_id(output.icd10_coding_id)
        assert stored is not None
        assert stored.differential_diagnosis_id == differential_diagnosis_id

    async def test_unknown_differential_diagnosis_raises(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        note_port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        use_case = _use_case(coding_repository, unit_of_work, note_port)

        with pytest.raises(DifferentialDiagnosisNotFoundError):
            await use_case.execute(
                _make_input(clinical_note_id=clinical_note_id, differential_diagnosis_id=uuid4())
            )

    async def test_differential_diagnosis_from_a_different_clinical_note_raises(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        other_clinical_note_id = uuid4()
        differential_diagnosis_id = uuid4()
        note_port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        diagnosis_port = FakeDifferentialDiagnosisQueryPort(
            existing_records={
                differential_diagnosis_id: make_differential_diagnosis_summary(
                    differential_diagnosis_id=differential_diagnosis_id,
                    clinical_note_id=other_clinical_note_id,
                )
            }
        )
        use_case = _use_case(coding_repository, unit_of_work, note_port, diagnosis_port)

        with pytest.raises(DifferentialDiagnosisClinicalNoteMismatchError):
            await use_case.execute(
                _make_input(
                    clinical_note_id=clinical_note_id,
                    differential_diagnosis_id=differential_diagnosis_id,
                )
            )
