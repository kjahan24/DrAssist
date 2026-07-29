"""Unit tests for the `UpdateClinicalReasoning` use case. No cross-module
port is constructed at all — see `domain/entities.py` for why this
module never checks the linked clinical note's editability."""

from uuid import uuid4

import pytest

from app.modules.clinical_reasoning.application.dto import UpdateClinicalReasoningInput
from app.modules.clinical_reasoning.application.use_cases.update_clinical_reasoning import (
    UpdateClinicalReasoning,
)
from app.modules.clinical_reasoning.domain.entities import ClinicalReasoning
from app.modules.clinical_reasoning.domain.enums import ReasoningSource
from app.modules.clinical_reasoning.domain.events import ClinicalReasoningUpdated
from app.modules.clinical_reasoning.domain.exceptions import (
    ClinicalReasoningNotEditableError,
    ClinicalReasoningNotFoundError,
)
from tests.unit.modules.clinical_reasoning.application.fakes import (
    FakeClinicalReasoningRepository,
    FakeUnitOfWork,
)


def _make_input(**overrides: object) -> UpdateClinicalReasoningInput:
    defaults: dict[str, object] = {"clinical_reasoning_id": uuid4()}
    defaults.update(overrides)
    return UpdateClinicalReasoningInput(**defaults)  # type: ignore[arg-type]


def _make_reasoning(**overrides: object) -> ClinicalReasoning:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "reasoning_source": ReasoningSource.AI,
        "reasoning_text": "Elevated WBC suggests possible infection.",
        "ai_generated": True,
    }
    defaults.update(overrides)
    return ClinicalReasoning.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def reasoning_repository() -> FakeClinicalReasoningRepository:
    return FakeClinicalReasoningRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    reasoning_repository: FakeClinicalReasoningRepository, unit_of_work: FakeUnitOfWork
) -> UpdateClinicalReasoning:
    return UpdateClinicalReasoning(
        clinical_reasoning_repository=reasoning_repository, unit_of_work=unit_of_work
    )


class TestUpdateClinicalReasoning:
    async def test_updates_fields_while_editable(
        self,
        reasoning_repository: FakeClinicalReasoningRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        reasoning = _make_reasoning()
        await reasoning_repository.add(reasoning)
        use_case = _use_case(reasoning_repository, unit_of_work)

        output = await use_case.execute(
            _make_input(clinical_reasoning_id=reasoning.id, reasoning_text="Revised assessment")
        )

        stored = await reasoning_repository.get_by_id(output.clinical_reasoning_id)
        assert stored is not None
        assert stored.reasoning_text == "Revised assessment"
        assert unit_of_work.committed is True
        assert any(isinstance(e, ClinicalReasoningUpdated) for e in unit_of_work.published_events)

    async def test_unknown_reasoning_record_raises(
        self,
        reasoning_repository: FakeClinicalReasoningRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = _use_case(reasoning_repository, unit_of_work)

        with pytest.raises(ClinicalReasoningNotFoundError):
            await use_case.execute(_make_input(clinical_reasoning_id=uuid4()))

    async def test_updating_an_approved_record_raises(
        self,
        reasoning_repository: FakeClinicalReasoningRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        reasoning = _make_reasoning()
        reasoning.approve()
        await reasoning_repository.add(reasoning)
        use_case = _use_case(reasoning_repository, unit_of_work)

        with pytest.raises(ClinicalReasoningNotEditableError):
            await use_case.execute(
                _make_input(clinical_reasoning_id=reasoning.id, reasoning_text="New")
            )
