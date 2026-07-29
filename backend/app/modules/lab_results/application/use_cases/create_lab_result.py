"""`CreateLabResult` — a lab result always extends exactly one existing
`LabOrder`, and a lab order may have at most one lab result.

Mirrors `app.modules.prescriptions.application.use_cases
.create_prescription.CreatePrescription`, one level deeper: resolves the
parent through `LabOrderQueryPort` and derives all four identity fields —
`organization_id`, `patient_id`, `visit_id`, `doctor_id` — from that
single lookup, which is what makes "Patient, Visit, Doctor, and
Organization must match the linked Lab Order" true unconditionally. A
missing lab order raises `LabOrderNotFoundError` (defined locally — see
`domain/exceptions.py` for why).

Unlike `CreatePrescription` (which also checks
`ClinicalNoteQueryPort.is_editable` before creating), this use case does
**not** check `LabOrderQueryPort.is_editable` — this task's business
rules never tie `LabResult` creation to `LabOrder`'s own status; see
`domain/entities.py` for the full reasoning. `result_number` must be
globally unique, the same treatment `order_number`/`prescription_number`
already receive.
"""

from app.modules.lab_orders.public.interfaces import LabOrderQueryPort
from app.modules.lab_results.application.dto import CreateLabResultInput, CreateLabResultOutput
from app.modules.lab_results.domain.entities import LabResult
from app.modules.lab_results.domain.exceptions import (
    DuplicateLabResultError,
    DuplicateResultNumberError,
    LabOrderNotFoundError,
)
from app.modules.lab_results.domain.repositories import LabResultRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreateLabResult(UseCase[CreateLabResultInput, CreateLabResultOutput]):
    def __init__(
        self,
        *,
        lab_result_repository: LabResultRepository,
        lab_order_query_port: LabOrderQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._lab_results = lab_result_repository
        self._lab_orders = lab_order_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: CreateLabResultInput) -> CreateLabResultOutput:
        lab_order_summary = await self._lab_orders.get_lab_order_summary(input_dto.lab_order_id)
        if lab_order_summary is None:
            raise LabOrderNotFoundError(input_dto.lab_order_id)

        existing_for_order = await self._lab_results.get_by_lab_order_id(input_dto.lab_order_id)
        if existing_for_order is not None:
            raise DuplicateLabResultError(input_dto.lab_order_id)

        existing_number = await self._lab_results.get_by_result_number(input_dto.result_number)
        if existing_number is not None:
            raise DuplicateResultNumberError(input_dto.result_number)

        lab_result = LabResult.create(
            organization_id=lab_order_summary.organization_id,
            lab_order_id=input_dto.lab_order_id,
            patient_id=lab_order_summary.patient_id,
            visit_id=lab_order_summary.visit_id,
            doctor_id=lab_order_summary.doctor_id,
            result_number=input_dto.result_number,
            reported_at=input_dto.reported_at,
            laboratory_name=input_dto.laboratory_name,
            comments=input_dto.comments,
        )
        await self._lab_results.add(lab_result)
        self._uow.collect_events(lab_result.pull_events())
        await self._uow.commit()

        return CreateLabResultOutput(
            lab_result_id=lab_result.id,
            organization_id=lab_result.organization_id,
            lab_order_id=lab_result.lab_order_id,
        )
