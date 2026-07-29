"""Unit tests for `VisitDiagnosisQueryService` — backs the module's
public `DiagnosisQueryPort` facade."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.modules.diagnosis.application.services.diagnosis_query_service import (
    VisitDiagnosisQueryService,
)
from app.modules.diagnosis.domain.entities import VisitDiagnosis
from app.modules.diagnosis.domain.enums import DiagnosisType
from tests.unit.modules.diagnosis.application.fakes import FakeVisitDiagnosisRepository


def _make_diagnosis(**overrides: object) -> VisitDiagnosis:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "visit_id": uuid4(),
        "sequence_number": 1,
        "diagnosis_name": "Type 2 diabetes",
        "diagnosis_type": DiagnosisType.PRIMARY,
        "diagnosed_at": datetime(2026, 1, 1, 9, 0),
    }
    defaults.update(overrides)
    return VisitDiagnosis.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def diagnosis_repo() -> FakeVisitDiagnosisRepository:
    return FakeVisitDiagnosisRepository()


@pytest.fixture
def service(diagnosis_repo: FakeVisitDiagnosisRepository) -> VisitDiagnosisQueryService:
    return VisitDiagnosisQueryService(diagnosis_repository=diagnosis_repo)


class TestDiagnosisExists:
    async def test_true_for_a_known_diagnosis(
        self,
        service: VisitDiagnosisQueryService,
        diagnosis_repo: FakeVisitDiagnosisRepository,
    ) -> None:
        diagnosis = _make_diagnosis()
        await diagnosis_repo.add(diagnosis)
        assert await service.diagnosis_exists(diagnosis.id) is True

    async def test_false_for_an_unknown_diagnosis(
        self, service: VisitDiagnosisQueryService
    ) -> None:
        assert await service.diagnosis_exists(uuid4()) is False


class TestListDiagnosesForVisit:
    async def test_returns_diagnoses_ordered_by_sequence_number(
        self,
        service: VisitDiagnosisQueryService,
        diagnosis_repo: FakeVisitDiagnosisRepository,
    ) -> None:
        visit_id = uuid4()
        await diagnosis_repo.add(
            _make_diagnosis(
                visit_id=visit_id,
                sequence_number=2,
                diagnosis_name="Hypertension",
                diagnosis_type=DiagnosisType.SECONDARY,
            )
        )
        await diagnosis_repo.add(
            _make_diagnosis(visit_id=visit_id, sequence_number=1, diagnosis_name="Type 2 diabetes")
        )

        summaries = await service.list_diagnoses_for_visit(visit_id)

        assert [s.sequence_number for s in summaries] == [1, 2]
        assert [s.diagnosis_name for s in summaries] == ["Type 2 diabetes", "Hypertension"]

    async def test_returns_empty_list_for_a_visit_without_diagnoses(
        self, service: VisitDiagnosisQueryService
    ) -> None:
        assert await service.list_diagnoses_for_visit(uuid4()) == []
