"""Unit tests for `DoctorReviewConsistencyService` — "Cross-module
consistency" for the `approved_*` checklist: a category claimed `True`
must have a backing record in its owning module."""

from uuid import UUID, uuid4

import pytest

from app.modules.doctor_review.application.services.doctor_review_consistency_service import (
    DoctorReviewConsistencyService,
)
from app.modules.doctor_review.domain.exceptions import ApprovedCategoryMissingRecordError
from tests.unit.modules.doctor_review.application.fakes import (
    FakeClinicalReasoningQueryPort,
    FakeDifferentialDiagnosisQueryPort,
    FakeICD10CodingQueryPort,
    FakeLabOrderQueryPort,
    FakeLabResultQueryPort,
    FakePrescriptionQueryPort,
    FakeSOAPNoteQueryPort,
    make_lab_order_summary,
)


def _service(
    *,
    soap_note_query_port: FakeSOAPNoteQueryPort | None = None,
    prescription_query_port: FakePrescriptionQueryPort | None = None,
    lab_order_query_port: FakeLabOrderQueryPort | None = None,
    lab_result_query_port: FakeLabResultQueryPort | None = None,
    clinical_reasoning_query_port: FakeClinicalReasoningQueryPort | None = None,
    differential_diagnosis_query_port: FakeDifferentialDiagnosisQueryPort | None = None,
    icd10_coding_query_port: FakeICD10CodingQueryPort | None = None,
) -> DoctorReviewConsistencyService:
    return DoctorReviewConsistencyService(
        soap_note_query_port=soap_note_query_port or FakeSOAPNoteQueryPort(),
        prescription_query_port=prescription_query_port or FakePrescriptionQueryPort(),
        lab_order_query_port=lab_order_query_port or FakeLabOrderQueryPort(),
        lab_result_query_port=lab_result_query_port or FakeLabResultQueryPort(),
        clinical_reasoning_query_port=clinical_reasoning_query_port
        or FakeClinicalReasoningQueryPort(),
        differential_diagnosis_query_port=differential_diagnosis_query_port
        or FakeDifferentialDiagnosisQueryPort(),
        icd10_coding_query_port=icd10_coding_query_port or FakeICD10CodingQueryPort(),
    )


async def _run(
    service: DoctorReviewConsistencyService, clinical_note_id: UUID, **overrides: object
) -> None:
    defaults: dict[str, object] = {
        "approved_soap_note": False,
        "approved_prescription": False,
        "approved_lab_orders": False,
        "approved_lab_results": False,
        "approved_reasoning": False,
        "approved_differential_diagnosis": False,
        "approved_icd10": False,
    }
    defaults.update(overrides)
    await service.ensure_approved_categories_exist(
        clinical_note_id=clinical_note_id,
        **defaults,  # type: ignore[arg-type]
    )


class TestAllFalseIsAlwaysValid:
    async def test_no_categories_approved_never_raises(self) -> None:
        await _run(_service(), uuid4())


class TestSoapNote:
    async def test_approved_with_existing_soap_note_passes(self) -> None:
        clinical_note_id = uuid4()
        port = FakeSOAPNoteQueryPort(clinical_notes_with_soap_note={clinical_note_id})
        await _run(_service(soap_note_query_port=port), clinical_note_id, approved_soap_note=True)

    async def test_approved_without_soap_note_raises(self) -> None:
        with pytest.raises(ApprovedCategoryMissingRecordError) as exc_info:
            await _run(_service(), uuid4(), approved_soap_note=True)
        assert exc_info.value.category == "soap_note"


class TestPrescription:
    async def test_approved_with_existing_prescription_passes(self) -> None:
        clinical_note_id = uuid4()
        port = FakePrescriptionQueryPort(clinical_notes_with_prescription={clinical_note_id})
        await _run(
            _service(prescription_query_port=port), clinical_note_id, approved_prescription=True
        )

    async def test_approved_without_prescription_raises(self) -> None:
        with pytest.raises(ApprovedCategoryMissingRecordError) as exc_info:
            await _run(_service(), uuid4(), approved_prescription=True)
        assert exc_info.value.category == "prescription"


class TestLabOrders:
    async def test_approved_with_existing_lab_orders_passes(self) -> None:
        clinical_note_id = uuid4()
        port = FakeLabOrderQueryPort(
            lab_orders_by_clinical_note={
                clinical_note_id: [make_lab_order_summary(clinical_note_id=clinical_note_id)]
            }
        )
        await _run(_service(lab_order_query_port=port), clinical_note_id, approved_lab_orders=True)

    async def test_approved_without_lab_orders_raises(self) -> None:
        with pytest.raises(ApprovedCategoryMissingRecordError) as exc_info:
            await _run(_service(), uuid4(), approved_lab_orders=True)
        assert exc_info.value.category == "lab_orders"


class TestLabResults:
    async def test_approved_with_a_lab_order_that_has_a_result_passes(self) -> None:
        clinical_note_id = uuid4()
        lab_order = make_lab_order_summary(clinical_note_id=clinical_note_id)
        lab_order_port = FakeLabOrderQueryPort(
            lab_orders_by_clinical_note={clinical_note_id: [lab_order]}
        )
        lab_result_port = FakeLabResultQueryPort(lab_orders_with_result={lab_order.lab_order_id})
        await _run(
            _service(lab_order_query_port=lab_order_port, lab_result_query_port=lab_result_port),
            clinical_note_id,
            approved_lab_results=True,
        )

    async def test_approved_with_a_lab_order_but_no_result_raises(self) -> None:
        clinical_note_id = uuid4()
        lab_order = make_lab_order_summary(clinical_note_id=clinical_note_id)
        lab_order_port = FakeLabOrderQueryPort(
            lab_orders_by_clinical_note={clinical_note_id: [lab_order]}
        )
        with pytest.raises(ApprovedCategoryMissingRecordError) as exc_info:
            await _run(
                _service(lab_order_query_port=lab_order_port),
                clinical_note_id,
                approved_lab_results=True,
            )
        assert exc_info.value.category == "lab_results"

    async def test_approved_with_no_lab_orders_at_all_raises(self) -> None:
        with pytest.raises(ApprovedCategoryMissingRecordError) as exc_info:
            await _run(_service(), uuid4(), approved_lab_results=True)
        assert exc_info.value.category == "lab_results"


class TestReasoning:
    async def test_approved_with_existing_reasoning_passes(self) -> None:
        clinical_note_id = uuid4()
        port = FakeClinicalReasoningQueryPort(
            reasoning_by_clinical_note={clinical_note_id: [object()]}  # type: ignore[dict-item]
        )
        await _run(
            _service(clinical_reasoning_query_port=port),
            clinical_note_id,
            approved_reasoning=True,
        )

    async def test_approved_without_reasoning_raises(self) -> None:
        with pytest.raises(ApprovedCategoryMissingRecordError) as exc_info:
            await _run(_service(), uuid4(), approved_reasoning=True)
        assert exc_info.value.category == "reasoning"


class TestDifferentialDiagnosis:
    async def test_approved_with_existing_diagnosis_passes(self) -> None:
        clinical_note_id = uuid4()
        port = FakeDifferentialDiagnosisQueryPort(
            diagnoses_by_clinical_note={clinical_note_id: [object()]}  # type: ignore[dict-item]
        )
        await _run(
            _service(differential_diagnosis_query_port=port),
            clinical_note_id,
            approved_differential_diagnosis=True,
        )

    async def test_approved_without_diagnosis_raises(self) -> None:
        with pytest.raises(ApprovedCategoryMissingRecordError) as exc_info:
            await _run(_service(), uuid4(), approved_differential_diagnosis=True)
        assert exc_info.value.category == "differential_diagnosis"


class TestICD10:
    async def test_approved_with_existing_code_passes(self) -> None:
        clinical_note_id = uuid4()
        port = FakeICD10CodingQueryPort(
            codings_by_clinical_note={clinical_note_id: [object()]}  # type: ignore[dict-item]
        )
        await _run(_service(icd10_coding_query_port=port), clinical_note_id, approved_icd10=True)

    async def test_approved_without_code_raises(self) -> None:
        with pytest.raises(ApprovedCategoryMissingRecordError) as exc_info:
            await _run(_service(), uuid4(), approved_icd10=True)
        assert exc_info.value.category == "icd10"
