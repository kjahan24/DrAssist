"""`ValidatePrescriptionContextUseCase` — an advisory, non-throwing "pre-
flight" check distinct from `PrescriptionContextInput.__post_init__`'s
structural (Tier 3) validation, the same shape
`app.modules.icd10_ai.application.use_cases.validate_clinical_context
.ValidateClinicalContextUseCase` establishes for its own module. Flags
completeness concerns a caller may want to surface before spending a
real generation call — several of these are safety-relevant specifically
to prescribing (missing allergy/medication history, missing pregnancy
status, missing weight for pediatric dosing), not just generic
"thin input" concerns.
"""

from app.modules.prescription_ai.application.dto import PrescriptionContextValidationResultDTO
from app.modules.prescription_ai.domain.enums import PatientSex, PrescribingSetting
from app.modules.prescription_ai.domain.value_objects import PrescriptionContextInput
from app.shared.application.use_case import UseCase


class ValidatePrescriptionContextUseCase(
    UseCase[PrescriptionContextInput, PrescriptionContextValidationResultDTO]
):
    async def execute(
        self, input_dto: PrescriptionContextInput
    ) -> PrescriptionContextValidationResultDTO:
        warnings: list[str] = []

        has_narrative_content = bool(
            (input_dto.history_of_present_illness or "").strip()
            or input_dto.symptoms
            or (input_dto.review_of_systems or "").strip()
            or (input_dto.physical_examination or "").strip()
        )
        if not has_narrative_content:
            warnings.append(
                "no HPI, symptoms, review of systems, or physical examination provided "
                "— prescription suggestions grounded only in the chief complaint may be "
                "unreliable"
            )

        has_clinical_summary = bool(
            (input_dto.assessment or "").strip()
            or (input_dto.plan or "").strip()
            or (input_dto.clinical_note or "").strip()
            or (input_dto.soap_note or "").strip()
        )
        if not has_clinical_summary:
            warnings.append(
                "no assessment, plan, clinical note, or SOAP note provided "
                "— consider supplying one for higher-confidence suggestions"
            )

        if not input_dto.allergies:
            warnings.append("no allergy information provided — cannot verify allergy safety")

        if not input_dto.existing_medications:
            warnings.append(
                "no existing medications provided — cannot check for drug interactions "
                "or duplicate therapy against the patient's current regimen"
            )

        is_pediatric_missing_weight = (
            input_dto.prescribing_setting is PrescribingSetting.PEDIATRIC
            and input_dto.weight_kg is None
        )
        if is_pediatric_missing_weight:
            warnings.append(
                "pediatric prescribing setting but no patient weight provided — pediatric "
                "dosing typically requires weight"
            )

        if input_dto.patient_sex is PatientSex.FEMALE and input_dto.pregnancy_status is None:
            warnings.append(
                "no pregnancy status provided for a female patient — required to assess "
                "pregnancy-related medication risk"
            )

        return PrescriptionContextValidationResultDTO(
            is_valid=True, errors=(), warnings=tuple(warnings)
        )
