"""Unit tests for `VisitProcedureQueryService` — backs the module's
public `ProcedureQueryPort` facade."""

from uuid import uuid4

import pytest

from app.modules.procedures.application.services.procedure_query_service import (
    VisitProcedureQueryService,
)
from app.modules.procedures.domain.entities import VisitProcedure
from tests.unit.modules.procedures.application.fakes import FakeVisitProcedureRepository


def _make_procedure(**overrides: object) -> VisitProcedure:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "visit_id": uuid4(),
        "sequence_number": 1,
        "procedure_name": "Wound dressing",
    }
    defaults.update(overrides)
    return VisitProcedure.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def procedure_repo() -> FakeVisitProcedureRepository:
    return FakeVisitProcedureRepository()


@pytest.fixture
def service(procedure_repo: FakeVisitProcedureRepository) -> VisitProcedureQueryService:
    return VisitProcedureQueryService(procedure_repository=procedure_repo)


class TestProcedureExists:
    async def test_true_for_a_known_procedure(
        self,
        service: VisitProcedureQueryService,
        procedure_repo: FakeVisitProcedureRepository,
    ) -> None:
        procedure = _make_procedure()
        await procedure_repo.add(procedure)
        assert await service.procedure_exists(procedure.id) is True

    async def test_false_for_an_unknown_procedure(
        self, service: VisitProcedureQueryService
    ) -> None:
        assert await service.procedure_exists(uuid4()) is False


class TestListProceduresForVisit:
    async def test_returns_procedures_ordered_by_sequence_number(
        self,
        service: VisitProcedureQueryService,
        procedure_repo: FakeVisitProcedureRepository,
    ) -> None:
        visit_id = uuid4()
        await procedure_repo.add(
            _make_procedure(visit_id=visit_id, sequence_number=2, procedure_name="Suturing")
        )
        await procedure_repo.add(
            _make_procedure(visit_id=visit_id, sequence_number=1, procedure_name="Wound dressing")
        )

        summaries = await service.list_procedures_for_visit(visit_id)

        assert [s.sequence_number for s in summaries] == [1, 2]
        assert [s.procedure_name for s in summaries] == ["Wound dressing", "Suturing"]

    async def test_returns_empty_list_for_a_visit_without_procedures(
        self, service: VisitProcedureQueryService
    ) -> None:
        assert await service.list_procedures_for_visit(uuid4()) == []
