"""Unit tests for `VisitChiefComplaintQueryService` — backs the module's
public `ChiefComplaintQueryPort` facade."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.modules.chief_complaints.application.services.chief_complaint_query_service import (
    VisitChiefComplaintQueryService,
)
from app.modules.chief_complaints.domain.entities import VisitChiefComplaint
from tests.unit.modules.chief_complaints.application.fakes import (
    FakeVisitChiefComplaintRepository,
)


def _make_chief_complaint(**overrides: object) -> VisitChiefComplaint:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "visit_id": uuid4(),
        "sequence_number": 1,
        "complaint": "Persistent cough",
        "recorded_at": datetime(2026, 1, 1, 9, 0),
    }
    defaults.update(overrides)
    return VisitChiefComplaint.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def chief_complaint_repo() -> FakeVisitChiefComplaintRepository:
    return FakeVisitChiefComplaintRepository()


@pytest.fixture
def service(
    chief_complaint_repo: FakeVisitChiefComplaintRepository,
) -> VisitChiefComplaintQueryService:
    return VisitChiefComplaintQueryService(chief_complaint_repository=chief_complaint_repo)


class TestChiefComplaintExists:
    async def test_true_for_a_known_chief_complaint(
        self,
        service: VisitChiefComplaintQueryService,
        chief_complaint_repo: FakeVisitChiefComplaintRepository,
    ) -> None:
        chief_complaint = _make_chief_complaint()
        await chief_complaint_repo.add(chief_complaint)
        assert await service.chief_complaint_exists(chief_complaint.id) is True

    async def test_false_for_an_unknown_chief_complaint(
        self, service: VisitChiefComplaintQueryService
    ) -> None:
        assert await service.chief_complaint_exists(uuid4()) is False


class TestListChiefComplaintsForVisit:
    async def test_returns_complaints_ordered_by_sequence_number(
        self,
        service: VisitChiefComplaintQueryService,
        chief_complaint_repo: FakeVisitChiefComplaintRepository,
    ) -> None:
        visit_id = uuid4()
        await chief_complaint_repo.add(
            _make_chief_complaint(visit_id=visit_id, sequence_number=2, complaint="Fatigue")
        )
        await chief_complaint_repo.add(
            _make_chief_complaint(visit_id=visit_id, sequence_number=1, complaint="Fever")
        )

        summaries = await service.list_chief_complaints_for_visit(visit_id)

        assert [s.sequence_number for s in summaries] == [1, 2]
        assert [s.complaint for s in summaries] == ["Fever", "Fatigue"]

    async def test_returns_empty_list_for_a_visit_without_complaints(
        self, service: VisitChiefComplaintQueryService
    ) -> None:
        assert await service.list_chief_complaints_for_visit(uuid4()) == []
