"""Unit tests for the `CreateDifferentialDiagnosis` use case, using
in-memory fakes for this module's own repository and the Clinical
Notes/Clinical Reasoning modules' public ports."""

from uuid import uuid4

import pytest

from app.modules.differential_diagnosis.application.dto import (
    CreateDifferentialDiagnosisInput,
)
from app.modules.differential_diagnosis.application.use_cases.create_differential_diagnosis import (  # noqa: E501
    CreateDifferentialDiagnosis,
)
from app.modules.differential_diagnosis.domain.enums import DiagnosisSource, ReviewStatus
from app.modules.differential_diagnosis.domain.events import DifferentialDiagnosisCreated
from app.modules.differential_diagnosis.domain.exceptions import (
    ClinicalNoteNotFoundError,
    ClinicalReasoningClinicalNoteMismatchError,
    ClinicalReasoningNotFoundError,
    DuplicateDiagnosisNameError,
    DuplicateRankingError,
)
from tests.unit.modules.differential_diagnosis.application.fakes import (
    FakeClinicalNoteQueryPort,
    FakeClinicalReasoningQueryPort,
    FakeDifferentialDiagnosisRepository,
    FakeUnitOfWork,
    make_clinical_note_summary,
    make_clinical_reasoning_summary,
)


def _make_input(**overrides: object) -> CreateDifferentialDiagnosisInput:
    defaults: dict[str, object] = {
        "clinical_note_id": uuid4(),
        "diagnosis_name": "Community-acquired pneumonia",
        "diagnosis_source": DiagnosisSource.AI,
        "ranking": 1,
    }
    defaults.update(overrides)
    return CreateDifferentialDiagnosisInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def diagnosis_repository() -> FakeDifferentialDiagnosisRepository:
    return FakeDifferentialDiagnosisRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    diagnosis_repository: FakeDifferentialDiagnosisRepository,
    unit_of_work: FakeUnitOfWork,
    clinical_note_query_port: FakeClinicalNoteQueryPort,
    clinical_reasoning_query_port: FakeClinicalReasoningQueryPort | None = None,
) -> CreateDifferentialDiagnosis:
    return CreateDifferentialDiagnosis(
        differential_diagnosis_repository=diagnosis_repository,
        clinical_note_query_port=clinical_note_query_port,
        clinical_reasoning_query_port=clinical_reasoning_query_port
        or FakeClinicalReasoningQueryPort(),
        unit_of_work=unit_of_work,
    )


class TestCreateDifferentialDiagnosis:
    async def test_creates_ai_generated_diagnosis_starting_pending(
        self,
        diagnosis_repository: FakeDifferentialDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
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
        use_case = _use_case(diagnosis_repository, unit_of_work, port)

        output = await use_case.execute(_make_input(clinical_note_id=clinical_note_id))

        assert output.review_status is ReviewStatus.PENDING
        stored = await diagnosis_repository.get_by_id(output.differential_diagnosis_id)
        assert stored is not None
        assert stored.organization_id == organization_id
        assert stored.patient_id == patient_id
        assert stored.visit_id == visit_id
        assert stored.doctor_id == doctor_id
        assert unit_of_work.committed is True
        assert any(
            isinstance(e, DifferentialDiagnosisCreated) for e in unit_of_work.published_events
        )

    async def test_creates_physician_authored_diagnosis_starting_reviewed(
        self,
        diagnosis_repository: FakeDifferentialDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(diagnosis_repository, unit_of_work, port)

        output = await use_case.execute(
            _make_input(
                clinical_note_id=clinical_note_id, diagnosis_source=DiagnosisSource.PHYSICIAN
            )
        )

        assert output.review_status is ReviewStatus.REVIEWED

    async def test_unknown_clinical_note_raises(
        self,
        diagnosis_repository: FakeDifferentialDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        port = FakeClinicalNoteQueryPort()
        use_case = _use_case(diagnosis_repository, unit_of_work, port)

        with pytest.raises(ClinicalNoteNotFoundError):
            await use_case.execute(_make_input(clinical_note_id=uuid4()))

    async def test_multiple_diagnoses_for_the_same_clinical_note_are_allowed(
        self,
        diagnosis_repository: FakeDifferentialDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(diagnosis_repository, unit_of_work, port)

        await use_case.execute(
            _make_input(clinical_note_id=clinical_note_id, diagnosis_name="Pneumonia", ranking=1)
        )
        output_b = await use_case.execute(
            _make_input(clinical_note_id=clinical_note_id, diagnosis_name="Bronchitis", ranking=2)
        )

        stored_b = await diagnosis_repository.get_by_id(output_b.differential_diagnosis_id)
        assert stored_b is not None
        assert stored_b.clinical_note_id == clinical_note_id

    async def test_duplicate_ranking_within_the_same_clinical_note_raises(
        self,
        diagnosis_repository: FakeDifferentialDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(diagnosis_repository, unit_of_work, port)
        await use_case.execute(
            _make_input(clinical_note_id=clinical_note_id, diagnosis_name="Pneumonia", ranking=1)
        )

        with pytest.raises(DuplicateRankingError):
            await use_case.execute(
                _make_input(
                    clinical_note_id=clinical_note_id, diagnosis_name="Bronchitis", ranking=1
                )
            )

    async def test_same_ranking_across_different_clinical_notes_is_allowed(
        self,
        diagnosis_repository: FakeDifferentialDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_a = uuid4()
        clinical_note_b = uuid4()
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_a: make_clinical_note_summary(clinical_note_id=clinical_note_a),
                clinical_note_b: make_clinical_note_summary(clinical_note_id=clinical_note_b),
            }
        )
        use_case = _use_case(diagnosis_repository, unit_of_work, port)

        await use_case.execute(_make_input(clinical_note_id=clinical_note_a, ranking=1))
        output_b = await use_case.execute(_make_input(clinical_note_id=clinical_note_b, ranking=1))

        stored_b = await diagnosis_repository.get_by_id(output_b.differential_diagnosis_id)
        assert stored_b is not None
        assert stored_b.ranking == 1

    async def test_duplicate_diagnosis_name_within_the_same_clinical_note_raises(
        self,
        diagnosis_repository: FakeDifferentialDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(diagnosis_repository, unit_of_work, port)
        await use_case.execute(
            _make_input(clinical_note_id=clinical_note_id, diagnosis_name="Pneumonia", ranking=1)
        )

        with pytest.raises(DuplicateDiagnosisNameError):
            await use_case.execute(
                _make_input(
                    clinical_note_id=clinical_note_id, diagnosis_name="pneumonia", ranking=2
                )
            )

    async def test_valid_clinical_reasoning_link_is_accepted(
        self,
        diagnosis_repository: FakeDifferentialDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_id = uuid4()
        clinical_reasoning_id = uuid4()
        note_port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        reasoning_port = FakeClinicalReasoningQueryPort(
            existing_records={
                clinical_reasoning_id: make_clinical_reasoning_summary(
                    clinical_reasoning_id=clinical_reasoning_id,
                    clinical_note_id=clinical_note_id,
                )
            }
        )
        use_case = _use_case(diagnosis_repository, unit_of_work, note_port, reasoning_port)

        output = await use_case.execute(
            _make_input(
                clinical_note_id=clinical_note_id, clinical_reasoning_id=clinical_reasoning_id
            )
        )

        stored = await diagnosis_repository.get_by_id(output.differential_diagnosis_id)
        assert stored is not None
        assert stored.clinical_reasoning_id == clinical_reasoning_id

    async def test_unknown_clinical_reasoning_raises(
        self,
        diagnosis_repository: FakeDifferentialDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_id = uuid4()
        note_port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        use_case = _use_case(diagnosis_repository, unit_of_work, note_port)

        with pytest.raises(ClinicalReasoningNotFoundError):
            await use_case.execute(
                _make_input(clinical_note_id=clinical_note_id, clinical_reasoning_id=uuid4())
            )

    async def test_clinical_reasoning_from_a_different_clinical_note_raises(
        self,
        diagnosis_repository: FakeDifferentialDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_id = uuid4()
        other_clinical_note_id = uuid4()
        clinical_reasoning_id = uuid4()
        note_port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        reasoning_port = FakeClinicalReasoningQueryPort(
            existing_records={
                clinical_reasoning_id: make_clinical_reasoning_summary(
                    clinical_reasoning_id=clinical_reasoning_id,
                    clinical_note_id=other_clinical_note_id,
                )
            }
        )
        use_case = _use_case(diagnosis_repository, unit_of_work, note_port, reasoning_port)

        with pytest.raises(ClinicalReasoningClinicalNoteMismatchError):
            await use_case.execute(
                _make_input(
                    clinical_note_id=clinical_note_id,
                    clinical_reasoning_id=clinical_reasoning_id,
                )
            )
