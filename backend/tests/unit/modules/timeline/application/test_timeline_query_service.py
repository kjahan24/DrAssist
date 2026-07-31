"""Unit tests for `TimelineQueryService` — patient/visit/appointment
validation, date-range and document-category filtering, sorting,
`chronological_order` assignment, and pagination."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.modules.appointment.public.dto import AppointmentSummaryDTO
from app.modules.documents.domain.enums import DocumentCategory
from app.modules.documents.public.dto import MedicalDocumentSummaryDTO
from app.modules.patient.public.dto import PatientSummaryDTO
from app.modules.timeline.application.dto import TimelineFilterInput
from app.modules.timeline.application.services.timeline_aggregation_service import (
    TimelineAggregationService,
)
from app.modules.timeline.application.services.timeline_query_service import (
    TimelineQueryService,
)
from app.modules.timeline.domain.exceptions import (
    AppointmentOwnershipMismatchError,
    PatientNotFoundError,
    VisitOwnershipMismatchError,
)
from app.modules.visit.public.dto import VisitSummaryDTO
from tests.unit.modules.timeline.application.fakes import (
    FakeAppointmentQueryPort,
    FakeClinicalNoteQueryPort,
    FakeDoctorReviewQueryPort,
    FakeDocumentQueryPort,
    FakeLabOrderQueryPort,
    FakeLabResultQueryPort,
    FakePatientQueryPort,
    FakePrescriptionQueryPort,
    FakeSOAPNoteQueryPort,
    FakeVisitQueryPort,
    make_appointment_summary,
    make_document_summary,
    make_patient_summary,
    make_visit_summary,
)


def _make_query_service(
    *,
    patients: list[PatientSummaryDTO] | None = None,
    visits: list[VisitSummaryDTO] | None = None,
    appointments: list[AppointmentSummaryDTO] | None = None,
    documents: list[MedicalDocumentSummaryDTO] | None = None,
) -> TimelineQueryService:
    appointment_port = FakeAppointmentQueryPort(appointments=appointments)
    visit_port = FakeVisitQueryPort(visits=visits)
    patient_port = FakePatientQueryPort(patients=patients)
    aggregation_service = TimelineAggregationService(
        appointment_query_port=appointment_port,
        visit_query_port=visit_port,
        clinical_note_query_port=FakeClinicalNoteQueryPort(),
        soap_note_query_port=FakeSOAPNoteQueryPort(),
        prescription_query_port=FakePrescriptionQueryPort(),
        lab_order_query_port=FakeLabOrderQueryPort(),
        lab_result_query_port=FakeLabResultQueryPort(),
        document_query_port=FakeDocumentQueryPort(documents=documents),
        patient_query_port=patient_port,
        doctor_review_query_port=FakeDoctorReviewQueryPort(),
    )
    return TimelineQueryService(
        aggregation_service=aggregation_service,
        patient_query_port=patient_port,
        visit_query_port=visit_port,
        appointment_query_port=appointment_port,
    )


class TestPatientValidation:
    async def test_unknown_patient_raises(self) -> None:
        service = _make_query_service()
        with pytest.raises(PatientNotFoundError):
            await service.get_patient_timeline(uuid4(), filters=TimelineFilterInput())


class TestVisitAndAppointmentOwnership:
    async def test_visit_id_belonging_to_a_different_patient_raises(self) -> None:
        patient = make_patient_summary()
        visit = make_visit_summary(patient_id=uuid4())
        service = _make_query_service(patients=[patient], visits=[visit])

        with pytest.raises(VisitOwnershipMismatchError):
            await service.get_patient_timeline(
                patient.patient_id,
                filters=TimelineFilterInput(visit_id=visit.visit_id),
            )

    async def test_unknown_visit_id_raises(self) -> None:
        patient = make_patient_summary()
        service = _make_query_service(patients=[patient])

        with pytest.raises(VisitOwnershipMismatchError):
            await service.get_patient_timeline(
                patient.patient_id, filters=TimelineFilterInput(visit_id=uuid4())
            )

    async def test_appointment_id_belonging_to_a_different_patient_raises(self) -> None:
        patient = make_patient_summary()
        appointment = make_appointment_summary(patient_id=uuid4())
        service = _make_query_service(patients=[patient], appointments=[appointment])

        with pytest.raises(AppointmentOwnershipMismatchError):
            await service.get_patient_timeline(
                patient.patient_id,
                filters=TimelineFilterInput(appointment_id=appointment.appointment_id),
            )

    async def test_visit_id_belonging_to_the_same_patient_is_accepted(self) -> None:
        patient = make_patient_summary()
        visit = make_visit_summary(patient_id=patient.patient_id)
        service = _make_query_service(patients=[patient], visits=[visit])

        page = await service.get_patient_timeline(
            patient.patient_id, filters=TimelineFilterInput(visit_id=visit.visit_id)
        )

        assert page.total == 1


class TestSortingAndChronologicalOrder:
    async def test_newest_first_is_the_default(self) -> None:
        patient = make_patient_summary()
        early = make_document_summary(
            patient_id=patient.patient_id,
            title="early",
            uploaded_at=datetime(2026, 1, 1, 9, 0),
        )
        late = make_document_summary(
            patient_id=patient.patient_id,
            title="late",
            uploaded_at=datetime(2026, 2, 1, 9, 0),
        )
        service = _make_query_service(patients=[patient], documents=[early, late])

        page = await service.get_patient_timeline(patient.patient_id, filters=TimelineFilterInput())

        assert [e.title for e in page.items] == ["late", "early"]
        assert [e.chronological_order for e in page.items] == [1, 2]

    async def test_oldest_first_when_requested(self) -> None:
        patient = make_patient_summary()
        early = make_document_summary(
            patient_id=patient.patient_id,
            title="early",
            uploaded_at=datetime(2026, 1, 1, 9, 0),
        )
        late = make_document_summary(
            patient_id=patient.patient_id,
            title="late",
            uploaded_at=datetime(2026, 2, 1, 9, 0),
        )
        service = _make_query_service(patients=[patient], documents=[early, late])

        page = await service.get_patient_timeline(
            patient.patient_id, filters=TimelineFilterInput(), sort_order="asc"
        )

        assert [e.title for e in page.items] == ["early", "late"]

    async def test_chronological_order_reflects_absolute_position_across_pages(self) -> None:
        patient = make_patient_summary()
        documents = [
            make_document_summary(
                patient_id=patient.patient_id,
                title=f"doc-{i}",
                uploaded_at=datetime(2026, 1, i + 1, 9, 0),
            )
            for i in range(5)
        ]
        service = _make_query_service(patients=[patient], documents=documents)

        second_page = await service.get_patient_timeline(
            patient.patient_id, filters=TimelineFilterInput(), offset=2, limit=2
        )

        assert [e.chronological_order for e in second_page.items] == [3, 4]


class TestPagination:
    async def test_total_reflects_the_full_filtered_count_not_the_page_size(self) -> None:
        patient = make_patient_summary()
        documents = [
            make_document_summary(
                patient_id=patient.patient_id, uploaded_at=datetime(2026, 1, i + 1, 9, 0)
            )
            for i in range(5)
        ]
        service = _make_query_service(patients=[patient], documents=documents)

        page = await service.get_patient_timeline(
            patient.patient_id, filters=TimelineFilterInput(), offset=0, limit=2
        )

        assert len(page.items) == 2
        assert page.total == 5
        assert page.offset == 0
        assert page.limit == 2


class TestDateRangeFiltering:
    async def test_date_from_and_date_to_narrow_the_results(self) -> None:
        patient = make_patient_summary()
        documents = [
            make_document_summary(
                patient_id=patient.patient_id,
                title=f"doc-{i}",
                uploaded_at=datetime(2026, 1, i + 1, 9, 0),
            )
            for i in range(5)
        ]
        service = _make_query_service(patients=[patient], documents=documents)

        page = await service.get_patient_timeline(
            patient.patient_id,
            filters=TimelineFilterInput(
                date_from=datetime(2026, 1, 2, 0, 0), date_to=datetime(2026, 1, 4, 23, 59)
            ),
        )

        assert page.total == 3


class TestDocumentCategoryFiltering:
    async def test_document_category_filter_excludes_non_matching_documents(self) -> None:
        patient = make_patient_summary()
        lab_report = make_document_summary(
            patient_id=patient.patient_id, category=DocumentCategory.LAB_REPORT
        )
        prescription_doc = make_document_summary(
            patient_id=patient.patient_id, category=DocumentCategory.PRESCRIPTION
        )
        service = _make_query_service(patients=[patient], documents=[lab_report, prescription_doc])

        page = await service.get_patient_timeline(
            patient.patient_id,
            filters=TimelineFilterInput(document_category=DocumentCategory.LAB_REPORT),
        )

        assert page.total == 1
        assert page.items[0].metadata is not None
        assert page.items[0].metadata["category"] == DocumentCategory.LAB_REPORT.value

    async def test_document_category_filter_scopes_out_non_document_events_too(self) -> None:
        """Unlike date range, `document_category` scopes the whole
        timeline to matching `DOCUMENT` events only — see
        `TimelineQueryService`'s own `_apply_document_category`
        docstring for the reasoning."""
        patient = make_patient_summary()
        lab_report = make_document_summary(
            patient_id=patient.patient_id, category=DocumentCategory.LAB_REPORT
        )
        service = _make_query_service(patients=[patient], documents=[lab_report])

        page = await service.get_patient_timeline(
            patient.patient_id,
            filters=TimelineFilterInput(document_category=DocumentCategory.PRESCRIPTION),
        )

        assert page.total == 0
