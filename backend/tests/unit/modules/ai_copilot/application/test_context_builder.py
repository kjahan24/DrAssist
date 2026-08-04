"""Unit tests for `ContextBuilder`."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from app.modules.ai_copilot.application.services.context_builder import ContextBuilder
from app.modules.ai_copilot.domain.exceptions import PatientNotFoundError
from tests.unit.modules.ai_copilot.application.fakes import (
    FakeClinicalNoteQueryPort,
    FakeLabResultQueryPort,
    FakePatientQueryPort,
    FakePrescriptionQueryPort,
    FakeSOAPNoteQueryPort,
    FakeTimelineQueryPort,
    FakeVisitQueryPort,
    make_allergy_summary,
    make_clinical_note_summary,
    make_condition_summary,
    make_lab_result_summary,
    make_patient_summary,
    make_prescription_summary,
    make_soap_note_summary,
    make_timeline_event,
    make_visit_summary,
)


class _Ports:
    def __init__(self) -> None:
        self.patients = FakePatientQueryPort()
        self.prescriptions = FakePrescriptionQueryPort()
        self.visits = FakeVisitQueryPort()
        self.clinical_notes = FakeClinicalNoteQueryPort()
        self.soap_notes = FakeSOAPNoteQueryPort()
        self.lab_results = FakeLabResultQueryPort()
        self.timeline = FakeTimelineQueryPort()

    def builder(self, *, max_items_per_source: int = 10) -> ContextBuilder:
        return ContextBuilder(
            patient_query_port=self.patients,
            prescription_query_port=self.prescriptions,
            visit_query_port=self.visits,
            clinical_note_query_port=self.clinical_notes,
            soap_note_query_port=self.soap_notes,
            lab_result_query_port=self.lab_results,
            timeline_query_port=self.timeline,
            max_items_per_source=max_items_per_source,
        )


class TestContextBuilder:
    async def test_raises_when_patient_does_not_exist(self) -> None:
        ports = _Ports()
        with pytest.raises(PatientNotFoundError):
            await ports.builder().build(uuid4())

    async def test_assembles_patient_and_empty_sections_when_nothing_else_exists(self) -> None:
        ports = _Ports()
        patient_id = uuid4()
        ports.patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)

        context = await ports.builder().build(patient_id)

        assert context.patient.patient_id == patient_id
        assert context.allergies == ()
        assert context.medications == ()
        assert context.conditions == ()
        assert context.visits == ()
        assert context.clinical_notes == ()
        assert context.soap_notes == ()
        assert context.lab_results == ()
        assert context.timeline_events == ()

    async def test_includes_allergies_and_conditions(self) -> None:
        ports = _Ports()
        patient_id = uuid4()
        ports.patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)
        ports.patients.allergies[patient_id] = [make_allergy_summary(patient_id=patient_id)]
        ports.patients.conditions[patient_id] = [make_condition_summary(patient_id=patient_id)]

        context = await ports.builder().build(patient_id)

        assert len(context.allergies) == 1
        assert len(context.conditions) == 1

    async def test_includes_medications_from_prescriptions_module(self) -> None:
        ports = _Ports()
        patient_id = uuid4()
        ports.patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)
        ports.prescriptions.prescriptions_by_patient[patient_id] = [
            make_prescription_summary(patient_id=patient_id)
        ]

        context = await ports.builder().build(patient_id)

        assert len(context.medications) == 1

    async def test_visits_are_sorted_most_recent_first(self) -> None:
        ports = _Ports()
        patient_id = uuid4()
        ports.patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)
        older = make_visit_summary(patient_id=patient_id, visit_date=date(2023, 1, 1))
        newer = make_visit_summary(patient_id=patient_id, visit_date=date(2024, 6, 1))
        ports.visits.visits_by_patient[patient_id] = [older, newer]

        context = await ports.builder().build(patient_id)

        assert context.visits[0].visit_id == newer.visit_id
        assert context.visits[1].visit_id == older.visit_id

    async def test_lists_are_bounded_by_max_items_per_source(self) -> None:
        ports = _Ports()
        patient_id = uuid4()
        ports.patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)
        ports.visits.visits_by_patient[patient_id] = [
            make_visit_summary(patient_id=patient_id) for _ in range(5)
        ]

        context = await ports.builder(max_items_per_source=2).build(patient_id)

        assert len(context.visits) == 2

    async def test_soap_notes_are_resolved_via_recent_clinical_notes(self) -> None:
        ports = _Ports()
        patient_id = uuid4()
        ports.patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)
        note = make_clinical_note_summary(patient_id=patient_id)
        ports.clinical_notes.notes_by_patient[patient_id] = [note]
        ports.soap_notes.soap_notes_by_clinical_note[note.clinical_note_id] = (
            make_soap_note_summary(clinical_note_id=note.clinical_note_id)
        )

        context = await ports.builder().build(patient_id)

        assert len(context.clinical_notes) == 1
        assert len(context.soap_notes) == 1
        assert context.soap_notes[0].clinical_note_id == note.clinical_note_id

    async def test_clinical_notes_without_a_soap_note_are_skipped_not_errored(self) -> None:
        ports = _Ports()
        patient_id = uuid4()
        ports.patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)
        note = make_clinical_note_summary(patient_id=patient_id)
        ports.clinical_notes.notes_by_patient[patient_id] = [note]
        # No SOAP note registered for this clinical note.

        context = await ports.builder().build(patient_id)

        assert context.clinical_notes[0].clinical_note_id == note.clinical_note_id
        assert context.soap_notes == ()

    async def test_includes_lab_results(self) -> None:
        ports = _Ports()
        patient_id = uuid4()
        ports.patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)
        ports.lab_results.results_by_patient[patient_id] = [
            make_lab_result_summary(patient_id=patient_id)
        ]

        context = await ports.builder().build(patient_id)

        assert len(context.lab_results) == 1

    async def test_includes_timeline_events(self) -> None:
        ports = _Ports()
        patient_id = uuid4()
        ports.patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)
        ports.timeline.events_by_patient[patient_id] = [make_timeline_event(patient_id=patient_id)]

        context = await ports.builder().build(patient_id)

        assert len(context.timeline_events) == 1

    async def test_timeline_filter_carries_visit_id_when_given(self) -> None:
        ports = _Ports()
        patient_id = uuid4()
        visit_id = uuid4()
        ports.patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)

        await ports.builder().build(patient_id, visit_id=visit_id)

        assert ports.timeline.received_filters[-1].visit_id == visit_id

    async def test_timeline_filter_has_no_visit_id_when_not_given(self) -> None:
        ports = _Ports()
        patient_id = uuid4()
        ports.patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)

        await ports.builder().build(patient_id)

        assert ports.timeline.received_filters[-1].visit_id is None

    async def test_medications_aggregate_across_multiple_prescriptions(self) -> None:
        ports = _Ports()
        patient_id = uuid4()
        ports.patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)
        ports.prescriptions.prescriptions_by_patient[patient_id] = [
            make_prescription_summary(patient_id=patient_id),
            make_prescription_summary(patient_id=patient_id),
        ]

        context = await ports.builder().build(patient_id)

        assert len(context.medications) == 2

    async def test_clinical_notes_are_sorted_most_recent_first(self) -> None:
        ports = _Ports()
        patient_id = uuid4()
        ports.patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)
        older = make_clinical_note_summary(
            patient_id=patient_id, encounter_datetime=datetime(2023, 1, 1, tzinfo=UTC)
        )
        newer = make_clinical_note_summary(
            patient_id=patient_id, encounter_datetime=datetime(2024, 6, 1, tzinfo=UTC)
        )
        ports.clinical_notes.notes_by_patient[patient_id] = [older, newer]

        context = await ports.builder().build(patient_id)

        assert context.clinical_notes[0].clinical_note_id == newer.clinical_note_id
        assert context.clinical_notes[1].clinical_note_id == older.clinical_note_id

    async def test_conditions_are_bounded_by_max_items_per_source(self) -> None:
        ports = _Ports()
        patient_id = uuid4()
        ports.patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)
        ports.patients.conditions[patient_id] = [
            make_condition_summary(patient_id=patient_id) for _ in range(4)
        ]

        context = await ports.builder(max_items_per_source=1).build(patient_id)

        assert len(context.conditions) == 1

    async def test_visit_without_a_visit_date_sorts_last(self) -> None:
        ports = _Ports()
        patient_id = uuid4()
        ports.patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)
        dated = make_visit_summary(patient_id=patient_id, visit_date=date(2024, 1, 1))
        undated = make_visit_summary(patient_id=patient_id, visit_date=None)
        ports.visits.visits_by_patient[patient_id] = [undated, dated]

        context = await ports.builder().build(patient_id)

        assert context.visits[0].visit_id == dated.visit_id
        assert context.visits[1].visit_id == undated.visit_id

    async def test_lab_results_are_bounded_by_max_items_per_source(self) -> None:
        ports = _Ports()
        patient_id = uuid4()
        ports.patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)
        ports.lab_results.results_by_patient[patient_id] = [
            make_lab_result_summary(patient_id=patient_id) for _ in range(5)
        ]

        context = await ports.builder(max_items_per_source=3).build(patient_id)

        assert len(context.lab_results) == 3

    async def test_soap_note_lookup_is_bounded_by_recent_clinical_notes_only(self) -> None:
        ports = _Ports()
        patient_id = uuid4()
        ports.patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)
        notes = [make_clinical_note_summary(patient_id=patient_id) for _ in range(3)]
        ports.clinical_notes.notes_by_patient[patient_id] = notes
        for note in notes:
            ports.soap_notes.soap_notes_by_clinical_note[note.clinical_note_id] = (
                make_soap_note_summary(clinical_note_id=note.clinical_note_id)
            )

        context = await ports.builder(max_items_per_source=2).build(patient_id)

        assert len(context.clinical_notes) == 2
        assert len(context.soap_notes) == 2
