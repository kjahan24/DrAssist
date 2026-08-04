"""`ValidateClinicalInputUseCase` — an advisory, non-throwing "pre-flight"
check distinct from `ClinicalEncounterInput.__post_init__`'s structural
(Tier 3) validation, which already guarantees every instance reaching
this use case has a non-blank `chief_complaint`/`language`. This use case
instead flags *completeness* concerns a caller (e.g. a future UI) may
want to surface before spending a real generation call: a chief complaint
alone constructs a valid `ClinicalEncounterInput`, but a note generated
from it alone will likely be thin.

`errors` currently never populates (every structural rule is already
enforced at construction) — the field exists so a future, stricter
completeness policy (e.g. "reject encounters with zero clinical content
at all") has somewhere to report without changing this DTO's shape.
"""

from app.modules.clinical_note_ai.application.dto import ValidationResultDTO
from app.modules.clinical_note_ai.domain.value_objects import ClinicalEncounterInput
from app.shared.application.use_case import UseCase


class ValidateClinicalInputUseCase(UseCase[ClinicalEncounterInput, ValidationResultDTO]):
    async def execute(self, input_dto: ClinicalEncounterInput) -> ValidationResultDTO:
        warnings: list[str] = []

        has_history = bool(
            (input_dto.history_of_present_illness or "").strip()
            or input_dto.symptoms
            or input_dto.observations
        )
        if not has_history:
            warnings.append(
                "no history of present illness, symptoms, or observations provided — "
                "the generated HPI section may be thin"
            )

        if not (input_dto.physical_examination or "").strip():
            warnings.append("no physical examination findings provided")

        if not (input_dto.assessment or "").strip() and not input_dto.diagnoses:
            warnings.append("no assessment or diagnoses provided")

        if not (input_dto.plan or "").strip():
            warnings.append("no plan provided")

        return ValidationResultDTO(is_valid=True, errors=(), warnings=tuple(warnings))
