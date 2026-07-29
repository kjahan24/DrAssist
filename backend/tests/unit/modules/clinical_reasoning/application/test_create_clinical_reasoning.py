"""Unit tests for the `CreateClinicalReasoning` use case, using in-memory
fakes for both this module's own repository and the Clinical Notes
module's public port."""

from uuid import uuid4

import pytest

from app.modules.clinical_reasoning.application.dto import CreateClinicalReasoningInput
from app.modules.clinical_reasoning.application.use_cases.create_clinical_reasoning import (
    CreateClinicalReasoning,
)
from app.modules.clinical_reasoning.domain.enums import ReasoningSource, ReviewStatus
from app.modules.clinical_reasoning.domain.events import ClinicalReasoningCreated
from app.modules.clinical_reasoning.domain.exceptions import ClinicalNoteNotFoundError
from tests.unit.modules.clinical_reasoning.application.fakes import (
    FakeClinicalNoteQueryPort,
    FakeClinicalReasoningRepository,
    FakeUnitOfWork,
    make_clinical_note_summary,
)


def _make_input(**overrides: object) -> CreateClinicalReasoningInput:
    defaults: dict[str, object] = {
        "clinical_note_id": uuid4(),
        "reasoning_source": ReasoningSource.AI,
        "reasoning_text": "Elevated WBC suggests possible infection.",
        "ai_generated": True,
    }
    defaults.update(overrides)
    return CreateClinicalReasoningInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def reasoning_repository() -> FakeClinicalReasoningRepository:
    return FakeClinicalReasoningRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    reasoning_repository: FakeClinicalReasoningRepository,
    unit_of_work: FakeUnitOfWork,
    clinical_note_query_port: FakeClinicalNoteQueryPort,
) -> CreateClinicalReasoning:
    return CreateClinicalReasoning(
        clinical_reasoning_repository=reasoning_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


class TestCreateClinicalReasoning:
    async def test_creates_ai_generated_reasoning_starting_pending(
        self,
        reasoning_repository: FakeClinicalReasoningRepository,
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
        use_case = _use_case(reasoning_repository, unit_of_work, port)

        output = await use_case.execute(
            _make_input(clinical_note_id=clinical_note_id, ai_generated=True)
        )

        assert output.review_status is ReviewStatus.PENDING
        stored = await reasoning_repository.get_by_id(output.clinical_reasoning_id)
        assert stored is not None
        assert stored.organization_id == organization_id
        assert stored.patient_id == patient_id
        assert stored.visit_id == visit_id
        assert stored.doctor_id == doctor_id
        assert stored.reviewed_by_doctor is False
        assert unit_of_work.committed is True
        assert any(isinstance(e, ClinicalReasoningCreated) for e in unit_of_work.published_events)

    async def test_creates_physician_authored_reasoning_starting_reviewed(
        self,
        reasoning_repository: FakeClinicalReasoningRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(reasoning_repository, unit_of_work, port)

        output = await use_case.execute(
            _make_input(
                clinical_note_id=clinical_note_id,
                ai_generated=False,
                reasoning_source=ReasoningSource.PHYSICIAN,
            )
        )

        assert output.review_status is ReviewStatus.REVIEWED
        stored = await reasoning_repository.get_by_id(output.clinical_reasoning_id)
        assert stored is not None
        assert stored.reviewed_by_doctor is True

    async def test_unknown_clinical_note_raises(
        self,
        reasoning_repository: FakeClinicalReasoningRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        port = FakeClinicalNoteQueryPort()
        use_case = _use_case(reasoning_repository, unit_of_work, port)

        with pytest.raises(ClinicalNoteNotFoundError):
            await use_case.execute(_make_input(clinical_note_id=uuid4()))

    async def test_multiple_reasoning_records_for_the_same_clinical_note_are_allowed(
        self,
        reasoning_repository: FakeClinicalReasoningRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(reasoning_repository, unit_of_work, port)

        await use_case.execute(
            _make_input(clinical_note_id=clinical_note_id, reasoning_text="First reasoning")
        )
        output_b = await use_case.execute(
            _make_input(clinical_note_id=clinical_note_id, reasoning_text="Second reasoning")
        )

        stored_b = await reasoning_repository.get_by_id(output_b.clinical_reasoning_id)
        assert stored_b is not None
        assert stored_b.clinical_note_id == clinical_note_id
