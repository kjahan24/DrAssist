"""`DoctorReviewConsistencyService` — enforces "Cross-module consistency"
for the `approved_*` checklist fields: a physician cannot attest to
having approved a documentation category that does not exist for the
linked Clinical Note.

This is the module's "domain service" in spirit — logic that spans more
than one aggregate and isn't naturally owned by `DoctorReview` itself —
but it lives in the *application* layer, not `domain/`, because it
requires I/O (reading seven peer modules' public ports). The domain
layer in this codebase never performs I/O (see every prior module's
`domain/entities.py`), so a literal `domain/services` package would
violate that boundary; this service is the same shape as
`app.modules.differential_diagnosis.application.use_cases
.create_differential_diagnosis.CreateDifferentialDiagnosis`'s own
cross-module consistency check, just factored out because it is reused
by both `CreateDoctorReview` and `UpdateDoctorReview` and spans eight
ports rather than one.

Only categories being newly marked `True` are checked — a category left
`False` (or explicitly set back to `False`) needs no backing record.
`approved_clinical_note` is not checked here: it is self-referential to
the Clinical Note this review already required to exist, so it is
trivially satisfiable.

Lab Results has no `list_..._for_clinical_note` port method (results are
keyed by `lab_order_id`, one-to-one — see
`app.modules.lab_results.public.interfaces.LabResultQueryPort`), so
`approved_lab_results` is checked by first listing this clinical note's
lab orders (via `LabOrderQueryPort`) and then checking each for a result
— the only path available through the existing public ports.
"""

from uuid import UUID

from app.modules.clinical_reasoning.public.interfaces import ClinicalReasoningQueryPort
from app.modules.differential_diagnosis.public.interfaces import DifferentialDiagnosisQueryPort
from app.modules.doctor_review.domain.exceptions import ApprovedCategoryMissingRecordError
from app.modules.icd10_coding.public.interfaces import ICD10CodingQueryPort
from app.modules.lab_orders.public.interfaces import LabOrderQueryPort
from app.modules.lab_results.public.interfaces import LabResultQueryPort
from app.modules.prescriptions.public.interfaces import PrescriptionQueryPort
from app.modules.soap_notes.public.interfaces import SOAPNoteQueryPort


class DoctorReviewConsistencyService:
    def __init__(
        self,
        *,
        soap_note_query_port: SOAPNoteQueryPort,
        prescription_query_port: PrescriptionQueryPort,
        lab_order_query_port: LabOrderQueryPort,
        lab_result_query_port: LabResultQueryPort,
        clinical_reasoning_query_port: ClinicalReasoningQueryPort,
        differential_diagnosis_query_port: DifferentialDiagnosisQueryPort,
        icd10_coding_query_port: ICD10CodingQueryPort,
    ) -> None:
        self._soap_notes = soap_note_query_port
        self._prescriptions = prescription_query_port
        self._lab_orders = lab_order_query_port
        self._lab_results = lab_result_query_port
        self._reasoning = clinical_reasoning_query_port
        self._differential_diagnoses = differential_diagnosis_query_port
        self._icd10_codings = icd10_coding_query_port

    async def ensure_approved_categories_exist(
        self,
        *,
        clinical_note_id: UUID,
        approved_soap_note: bool,
        approved_prescription: bool,
        approved_lab_orders: bool,
        approved_lab_results: bool,
        approved_reasoning: bool,
        approved_differential_diagnosis: bool,
        approved_icd10: bool,
    ) -> None:
        if approved_soap_note and not await self._soap_notes.soap_note_exists_for_clinical_note(
            clinical_note_id
        ):
            raise ApprovedCategoryMissingRecordError("soap_note", clinical_note_id)

        if (
            approved_prescription
            and not await self._prescriptions.prescription_exists_for_clinical_note(
                clinical_note_id
            )
        ):
            raise ApprovedCategoryMissingRecordError("prescription", clinical_note_id)

        lab_orders = None
        if approved_lab_orders or approved_lab_results:
            lab_orders = await self._lab_orders.list_lab_orders_for_clinical_note(clinical_note_id)

        if approved_lab_orders and not lab_orders:
            raise ApprovedCategoryMissingRecordError("lab_orders", clinical_note_id)

        if approved_lab_results:
            assert lab_orders is not None
            has_result = False
            for lab_order in lab_orders:
                if await self._lab_results.lab_result_exists_for_lab_order(lab_order.lab_order_id):
                    has_result = True
                    break
            if not has_result:
                raise ApprovedCategoryMissingRecordError("lab_results", clinical_note_id)

        if (
            approved_reasoning
            and not await self._reasoning.list_clinical_reasoning_for_clinical_note(
                clinical_note_id
            )
        ):
            raise ApprovedCategoryMissingRecordError("reasoning", clinical_note_id)

        if approved_differential_diagnosis:
            differential_diagnoses = (
                await self._differential_diagnoses.list_differential_diagnoses_for_clinical_note(
                    clinical_note_id
                )
            )
            if not differential_diagnoses:
                raise ApprovedCategoryMissingRecordError("differential_diagnosis", clinical_note_id)

        if approved_icd10 and not await self._icd10_codings.list_icd10_codings_for_clinical_note(
            clinical_note_id
        ):
            raise ApprovedCategoryMissingRecordError("icd10", clinical_note_id)
