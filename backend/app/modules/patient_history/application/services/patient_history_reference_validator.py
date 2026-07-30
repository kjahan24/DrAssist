"""`PatientHistoryReferenceValidator` — enforces "Reference validation"
and "Cross-module consistency" for a `(reference_type, reference_id)`
pair: the named artifact must exist, in its own owning module, and
belong to the *same clinical encounter* as the approving Doctor Review.

Dispatches on `reference_type` to exactly the peer module whose id space
`reference_id` lives in. `ReferenceType.CLINICAL_REASONING` does not
exist in this task's `ReferenceType` enum — Clinical Reasoning is not
one of the eight artifact kinds `PatientHistory` can directly reference,
so this validator (and this module generally) has no dependency on
`ClinicalReasoningQueryPort`; reasoning that informed a diagnosis is
already reachable transitively through that diagnosis's own optional
link (see `app.modules.differential_diagnosis.domain.entities
.DifferentialDiagnosis.clinical_reasoning_id`).

`SOAPNoteQueryPort`/`PrescriptionQueryPort` expose no id-keyed lookup at
all (both are one-to-one children of `ClinicalNote` and are only
queryable *by* `clinical_note_id` — see their own `public/interfaces.py`
docstrings). Validating `reference_id` for those two therefore means
looking the child up *by* the encounter's `clinical_note_id` and then
confirming the returned summary's own id matches `reference_id` — the
only path the existing public ports make available, and the same
indirect-lookup technique
`app.modules.doctor_review.application.services
.doctor_review_consistency_service.DoctorReviewConsistencyService`
already established for `LabResult` (itself reused again below, since
`LabResultQueryPort.get_lab_result_summary` is keyed by `lab_order_id`,
not `lab_result_id`).
"""

from uuid import UUID

from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.differential_diagnosis.public.interfaces import DifferentialDiagnosisQueryPort
from app.modules.doctor_review.public.dto import DoctorReviewSummaryDTO
from app.modules.icd10_coding.public.interfaces import ICD10CodingQueryPort
from app.modules.lab_orders.public.interfaces import LabOrderQueryPort
from app.modules.lab_results.public.interfaces import LabResultQueryPort
from app.modules.patient_history.domain.enums import ReferenceType
from app.modules.patient_history.domain.exceptions import ReferenceNotFoundError
from app.modules.prescriptions.public.interfaces import PrescriptionQueryPort
from app.modules.soap_notes.public.interfaces import SOAPNoteQueryPort


class PatientHistoryReferenceValidator:
    def __init__(
        self,
        *,
        clinical_note_query_port: ClinicalNoteQueryPort,
        soap_note_query_port: SOAPNoteQueryPort,
        prescription_query_port: PrescriptionQueryPort,
        lab_order_query_port: LabOrderQueryPort,
        lab_result_query_port: LabResultQueryPort,
        differential_diagnosis_query_port: DifferentialDiagnosisQueryPort,
        icd10_coding_query_port: ICD10CodingQueryPort,
    ) -> None:
        self._clinical_notes = clinical_note_query_port
        self._soap_notes = soap_note_query_port
        self._prescriptions = prescription_query_port
        self._lab_orders = lab_order_query_port
        self._lab_results = lab_result_query_port
        self._differential_diagnoses = differential_diagnosis_query_port
        self._icd10_codings = icd10_coding_query_port

    async def validate(
        self,
        *,
        reference_type: ReferenceType,
        reference_id: UUID,
        doctor_review_summary: DoctorReviewSummaryDTO,
    ) -> None:
        clinical_note_id = doctor_review_summary.clinical_note_id

        match reference_type:
            case ReferenceType.CLINICAL_NOTE:
                note = await self._clinical_notes.get_clinical_note_summary(reference_id)
                if note is None or note.clinical_note_id != clinical_note_id:
                    raise ReferenceNotFoundError(reference_type.value, reference_id)

            case ReferenceType.SOAP_NOTE:
                soap_note = await self._soap_notes.get_soap_note_summary(clinical_note_id)
                if soap_note is None or soap_note.soap_note_id != reference_id:
                    raise ReferenceNotFoundError(reference_type.value, reference_id)

            case ReferenceType.PRESCRIPTION:
                prescription = await self._prescriptions.get_prescription_summary(clinical_note_id)
                if prescription is None or prescription.prescription_id != reference_id:
                    raise ReferenceNotFoundError(reference_type.value, reference_id)

            case ReferenceType.LAB_ORDER:
                lab_order = await self._lab_orders.get_lab_order_summary(reference_id)
                if lab_order is None or lab_order.clinical_note_id != clinical_note_id:
                    raise ReferenceNotFoundError(reference_type.value, reference_id)

            case ReferenceType.LAB_RESULT:
                lab_orders = await self._lab_orders.list_lab_orders_for_clinical_note(
                    clinical_note_id
                )
                found = False
                for lab_order in lab_orders:
                    result = await self._lab_results.get_lab_result_summary(lab_order.lab_order_id)
                    if result is not None and result.lab_result_id == reference_id:
                        found = True
                        break
                if not found:
                    raise ReferenceNotFoundError(reference_type.value, reference_id)

            case ReferenceType.DIFFERENTIAL_DIAGNOSIS:
                diagnosis = await self._differential_diagnoses.get_differential_diagnosis_summary(
                    reference_id
                )
                if diagnosis is None or diagnosis.clinical_note_id != clinical_note_id:
                    raise ReferenceNotFoundError(reference_type.value, reference_id)

            case ReferenceType.ICD10:
                coding = await self._icd10_codings.get_icd10_coding_summary(reference_id)
                if coding is None or coding.clinical_note_id != clinical_note_id:
                    raise ReferenceNotFoundError(reference_type.value, reference_id)

            case ReferenceType.DOCTOR_REVIEW:
                if reference_id != doctor_review_summary.doctor_review_id:
                    raise ReferenceNotFoundError(reference_type.value, reference_id)
