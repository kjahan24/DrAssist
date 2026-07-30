"""Unit tests for `PatientHistoryReferenceValidator` — "Reference
validation" and "Cross-module consistency" for each of the eight
`ReferenceType` values."""

from uuid import uuid4

import pytest

from app.modules.patient_history.application.services.patient_history_reference_validator import (
    PatientHistoryReferenceValidator,
)
from app.modules.patient_history.domain.enums import ReferenceType
from app.modules.patient_history.domain.exceptions import ReferenceNotFoundError
from tests.unit.modules.patient_history.application.fakes import (
    FakeClinicalNoteQueryPort,
    FakeDifferentialDiagnosisQueryPort,
    FakeICD10CodingQueryPort,
    FakeLabOrderQueryPort,
    FakeLabResultQueryPort,
    FakePrescriptionQueryPort,
    FakeSOAPNoteQueryPort,
    make_clinical_note_summary,
    make_differential_diagnosis_summary,
    make_doctor_review_summary,
    make_icd10_coding_summary,
    make_lab_order_summary,
    make_lab_result_summary,
    make_prescription_summary,
    make_soap_note_summary,
)


def _validator(
    *,
    clinical_note_query_port: FakeClinicalNoteQueryPort | None = None,
    soap_note_query_port: FakeSOAPNoteQueryPort | None = None,
    prescription_query_port: FakePrescriptionQueryPort | None = None,
    lab_order_query_port: FakeLabOrderQueryPort | None = None,
    lab_result_query_port: FakeLabResultQueryPort | None = None,
    differential_diagnosis_query_port: FakeDifferentialDiagnosisQueryPort | None = None,
    icd10_coding_query_port: FakeICD10CodingQueryPort | None = None,
) -> PatientHistoryReferenceValidator:
    return PatientHistoryReferenceValidator(
        clinical_note_query_port=clinical_note_query_port or FakeClinicalNoteQueryPort(),
        soap_note_query_port=soap_note_query_port or FakeSOAPNoteQueryPort(),
        prescription_query_port=prescription_query_port or FakePrescriptionQueryPort(),
        lab_order_query_port=lab_order_query_port or FakeLabOrderQueryPort(),
        lab_result_query_port=lab_result_query_port or FakeLabResultQueryPort(),
        differential_diagnosis_query_port=differential_diagnosis_query_port
        or FakeDifferentialDiagnosisQueryPort(),
        icd10_coding_query_port=icd10_coding_query_port or FakeICD10CodingQueryPort(),
    )


class TestClinicalNote:
    async def test_matching_clinical_note_passes(self) -> None:
        clinical_note_id = uuid4()
        review = make_doctor_review_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        await _validator(clinical_note_query_port=port).validate(
            reference_type=ReferenceType.CLINICAL_NOTE,
            reference_id=clinical_note_id,
            doctor_review_summary=review,
        )

    async def test_unknown_clinical_note_raises(self) -> None:
        review = make_doctor_review_summary()
        with pytest.raises(ReferenceNotFoundError):
            await _validator().validate(
                reference_type=ReferenceType.CLINICAL_NOTE,
                reference_id=uuid4(),
                doctor_review_summary=review,
            )

    async def test_clinical_note_from_a_different_encounter_raises(self) -> None:
        clinical_note_id = uuid4()
        other_note_id = uuid4()
        review = make_doctor_review_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                other_note_id: make_clinical_note_summary(clinical_note_id=other_note_id)
            }
        )
        with pytest.raises(ReferenceNotFoundError):
            await _validator(clinical_note_query_port=port).validate(
                reference_type=ReferenceType.CLINICAL_NOTE,
                reference_id=other_note_id,
                doctor_review_summary=review,
            )


class TestSoapNote:
    async def test_matching_soap_note_passes(self) -> None:
        clinical_note_id = uuid4()
        soap_note_id = uuid4()
        review = make_doctor_review_summary(clinical_note_id=clinical_note_id)
        port = FakeSOAPNoteQueryPort(
            summary_by_clinical_note={
                clinical_note_id: make_soap_note_summary(
                    soap_note_id=soap_note_id, clinical_note_id=clinical_note_id
                )
            }
        )
        await _validator(soap_note_query_port=port).validate(
            reference_type=ReferenceType.SOAP_NOTE,
            reference_id=soap_note_id,
            doctor_review_summary=review,
        )

    async def test_no_soap_note_for_the_encounter_raises(self) -> None:
        review = make_doctor_review_summary()
        with pytest.raises(ReferenceNotFoundError):
            await _validator().validate(
                reference_type=ReferenceType.SOAP_NOTE,
                reference_id=uuid4(),
                doctor_review_summary=review,
            )

    async def test_mismatched_soap_note_id_raises(self) -> None:
        clinical_note_id = uuid4()
        review = make_doctor_review_summary(clinical_note_id=clinical_note_id)
        port = FakeSOAPNoteQueryPort(
            summary_by_clinical_note={
                clinical_note_id: make_soap_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        with pytest.raises(ReferenceNotFoundError):
            await _validator(soap_note_query_port=port).validate(
                reference_type=ReferenceType.SOAP_NOTE,
                reference_id=uuid4(),
                doctor_review_summary=review,
            )


class TestPrescription:
    async def test_matching_prescription_passes(self) -> None:
        clinical_note_id = uuid4()
        prescription_id = uuid4()
        review = make_doctor_review_summary(clinical_note_id=clinical_note_id)
        port = FakePrescriptionQueryPort(
            summary_by_clinical_note={
                clinical_note_id: make_prescription_summary(
                    prescription_id=prescription_id, clinical_note_id=clinical_note_id
                )
            }
        )
        await _validator(prescription_query_port=port).validate(
            reference_type=ReferenceType.PRESCRIPTION,
            reference_id=prescription_id,
            doctor_review_summary=review,
        )

    async def test_no_prescription_for_the_encounter_raises(self) -> None:
        review = make_doctor_review_summary()
        with pytest.raises(ReferenceNotFoundError):
            await _validator().validate(
                reference_type=ReferenceType.PRESCRIPTION,
                reference_id=uuid4(),
                doctor_review_summary=review,
            )


class TestLabOrder:
    async def test_matching_lab_order_passes(self) -> None:
        clinical_note_id = uuid4()
        lab_order_id = uuid4()
        review = make_doctor_review_summary(clinical_note_id=clinical_note_id)
        port = FakeLabOrderQueryPort(
            lab_orders_by_id={
                lab_order_id: make_lab_order_summary(
                    lab_order_id=lab_order_id, clinical_note_id=clinical_note_id
                )
            }
        )
        await _validator(lab_order_query_port=port).validate(
            reference_type=ReferenceType.LAB_ORDER,
            reference_id=lab_order_id,
            doctor_review_summary=review,
        )

    async def test_unknown_lab_order_raises(self) -> None:
        review = make_doctor_review_summary()
        with pytest.raises(ReferenceNotFoundError):
            await _validator().validate(
                reference_type=ReferenceType.LAB_ORDER,
                reference_id=uuid4(),
                doctor_review_summary=review,
            )

    async def test_lab_order_from_a_different_encounter_raises(self) -> None:
        clinical_note_id = uuid4()
        lab_order_id = uuid4()
        review = make_doctor_review_summary(clinical_note_id=clinical_note_id)
        port = FakeLabOrderQueryPort(
            lab_orders_by_id={
                lab_order_id: make_lab_order_summary(
                    lab_order_id=lab_order_id, clinical_note_id=uuid4()
                )
            }
        )
        with pytest.raises(ReferenceNotFoundError):
            await _validator(lab_order_query_port=port).validate(
                reference_type=ReferenceType.LAB_ORDER,
                reference_id=lab_order_id,
                doctor_review_summary=review,
            )


class TestLabResult:
    async def test_matching_lab_result_passes(self) -> None:
        clinical_note_id = uuid4()
        lab_order_id = uuid4()
        lab_result_id = uuid4()
        review = make_doctor_review_summary(clinical_note_id=clinical_note_id)
        lab_order_port = FakeLabOrderQueryPort(
            lab_orders_by_clinical_note={
                clinical_note_id: [
                    make_lab_order_summary(
                        lab_order_id=lab_order_id, clinical_note_id=clinical_note_id
                    )
                ]
            }
        )
        lab_result_port = FakeLabResultQueryPort(
            results_by_lab_order={
                lab_order_id: make_lab_result_summary(
                    lab_result_id=lab_result_id, lab_order_id=lab_order_id
                )
            }
        )
        await _validator(
            lab_order_query_port=lab_order_port, lab_result_query_port=lab_result_port
        ).validate(
            reference_type=ReferenceType.LAB_RESULT,
            reference_id=lab_result_id,
            doctor_review_summary=review,
        )

    async def test_no_lab_orders_at_all_raises(self) -> None:
        review = make_doctor_review_summary()
        with pytest.raises(ReferenceNotFoundError):
            await _validator().validate(
                reference_type=ReferenceType.LAB_RESULT,
                reference_id=uuid4(),
                doctor_review_summary=review,
            )

    async def test_lab_order_without_a_matching_result_raises(self) -> None:
        clinical_note_id = uuid4()
        lab_order_id = uuid4()
        review = make_doctor_review_summary(clinical_note_id=clinical_note_id)
        lab_order_port = FakeLabOrderQueryPort(
            lab_orders_by_clinical_note={
                clinical_note_id: [
                    make_lab_order_summary(
                        lab_order_id=lab_order_id, clinical_note_id=clinical_note_id
                    )
                ]
            }
        )
        with pytest.raises(ReferenceNotFoundError):
            await _validator(lab_order_query_port=lab_order_port).validate(
                reference_type=ReferenceType.LAB_RESULT,
                reference_id=uuid4(),
                doctor_review_summary=review,
            )


class TestDifferentialDiagnosis:
    async def test_matching_diagnosis_passes(self) -> None:
        clinical_note_id = uuid4()
        diagnosis_id = uuid4()
        review = make_doctor_review_summary(clinical_note_id=clinical_note_id)
        port = FakeDifferentialDiagnosisQueryPort(
            existing_records={
                diagnosis_id: make_differential_diagnosis_summary(
                    differential_diagnosis_id=diagnosis_id, clinical_note_id=clinical_note_id
                )
            }
        )
        await _validator(differential_diagnosis_query_port=port).validate(
            reference_type=ReferenceType.DIFFERENTIAL_DIAGNOSIS,
            reference_id=diagnosis_id,
            doctor_review_summary=review,
        )

    async def test_unknown_diagnosis_raises(self) -> None:
        review = make_doctor_review_summary()
        with pytest.raises(ReferenceNotFoundError):
            await _validator().validate(
                reference_type=ReferenceType.DIFFERENTIAL_DIAGNOSIS,
                reference_id=uuid4(),
                doctor_review_summary=review,
            )


class TestICD10:
    async def test_matching_code_passes(self) -> None:
        clinical_note_id = uuid4()
        coding_id = uuid4()
        review = make_doctor_review_summary(clinical_note_id=clinical_note_id)
        port = FakeICD10CodingQueryPort(
            existing_codings={
                coding_id: make_icd10_coding_summary(
                    icd10_coding_id=coding_id, clinical_note_id=clinical_note_id
                )
            }
        )
        await _validator(icd10_coding_query_port=port).validate(
            reference_type=ReferenceType.ICD10,
            reference_id=coding_id,
            doctor_review_summary=review,
        )

    async def test_unknown_code_raises(self) -> None:
        review = make_doctor_review_summary()
        with pytest.raises(ReferenceNotFoundError):
            await _validator().validate(
                reference_type=ReferenceType.ICD10,
                reference_id=uuid4(),
                doctor_review_summary=review,
            )


class TestDoctorReview:
    async def test_matching_doctor_review_id_passes(self) -> None:
        review = make_doctor_review_summary()
        await _validator().validate(
            reference_type=ReferenceType.DOCTOR_REVIEW,
            reference_id=review.doctor_review_id,
            doctor_review_summary=review,
        )

    async def test_mismatched_doctor_review_id_raises(self) -> None:
        review = make_doctor_review_summary()
        with pytest.raises(ReferenceNotFoundError):
            await _validator().validate(
                reference_type=ReferenceType.DOCTOR_REVIEW,
                reference_id=uuid4(),
                doctor_review_summary=review,
            )
