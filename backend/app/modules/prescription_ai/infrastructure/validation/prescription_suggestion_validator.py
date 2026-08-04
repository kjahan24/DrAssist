"""`DefaultPrescriptionSuggestionValidator` — the one concrete
`PrescriptionSuggestionValidatorPort` implementation this task ships, per
"VALIDATION — missing dosage, missing duration, missing frequency,
invalid medication structure, malformed JSON, duplicated medications,
hallucinated medications, empty responses" ("malformed JSON" is
`PrescriptionSuggestionParserPort`'s concern — a suggestion set that
reaches this validator already parsed successfully, so only content-level
checks remain here, the same split
`app.modules.icd10_ai.infrastructure.validation.icd10_suggestion_validator
.DefaultICD10SuggestionValidator` documents for itself).

Reuses `app.shared.infrastructure.text_processing.placeholder_detection
.find_placeholder_marker` (rule: "Reuse... Shared validation framework...
Avoid duplicate implementations").

No port dependency — unlike `DefaultICD10SuggestionValidator`, "invalid
medication structure" here means only a structurally incomplete record
(a blank `generic_name`), which needs no external knowledge lookup (see
`MedicationKnowledgePort`'s own docstring for why medication names have
no rigid format to validate against the way ICD-10 codes do).

Checks run in this order, each a distinct failure mode with its own
domain exception:

1. Zero medications -> `EmptyPrescriptionResponseError`.
2. Any medication with a blank `generic_name` ->
   `InvalidMedicationStructureError`.
3. Any two medications sharing the same normalized `generic_name` ->
   `DuplicateMedicationError`.
4. Any medication with a blank `dosage` -> `MissingMedicationDosageError`.
5. Any medication with a blank `frequency` ->
   `MissingMedicationFrequencyError`.
6. Any medication with a blank `duration` ->
   `MissingMedicationDurationError`.
7. Any medication whose `clinical_indication`, `clinical_reasoning`,
   `monitoring_advice`, or `patient_instructions` contains a recognized
   placeholder marker -> `HallucinatedMedicationError`.
"""

from app.modules.prescription_ai.application.ports import PrescriptionSuggestionValidatorPort
from app.modules.prescription_ai.domain.exceptions import (
    DuplicateMedicationError,
    EmptyPrescriptionResponseError,
    HallucinatedMedicationError,
    InvalidMedicationStructureError,
    MissingMedicationDosageError,
    MissingMedicationDurationError,
    MissingMedicationFrequencyError,
)
from app.modules.prescription_ai.domain.value_objects import (
    MedicationSuggestion,
    PrescriptionSuggestionSet,
)
from app.shared.infrastructure.text_processing.placeholder_detection import (
    find_placeholder_marker,
)


class DefaultPrescriptionSuggestionValidator(PrescriptionSuggestionValidatorPort):
    def validate(self, suggestion_set: PrescriptionSuggestionSet) -> None:
        if suggestion_set.is_empty:
            raise EmptyPrescriptionResponseError()

        self._check_structure_and_duplicates(suggestion_set.medications)

        for medication in suggestion_set.medications:
            self._check_required_fields(medication)

        for medication in suggestion_set.medications:
            self._check_no_hallucinated_placeholders(medication)

    def _check_structure_and_duplicates(
        self, medications: tuple[MedicationSuggestion, ...]
    ) -> None:
        seen_names: set[str] = set()
        for medication in medications:
            if not medication.generic_name.strip():
                raise InvalidMedicationStructureError("generic_name must not be blank")
            normalized = medication.generic_name.strip().lower()
            if normalized in seen_names:
                raise DuplicateMedicationError(medication.generic_name)
            seen_names.add(normalized)

    def _check_required_fields(self, medication: MedicationSuggestion) -> None:
        if not medication.dosage.strip():
            raise MissingMedicationDosageError(medication.generic_name)
        if not medication.frequency.strip():
            raise MissingMedicationFrequencyError(medication.generic_name)
        if not medication.duration.strip():
            raise MissingMedicationDurationError(medication.generic_name)

    def _check_no_hallucinated_placeholders(self, medication: MedicationSuggestion) -> None:
        for field_value in (
            medication.clinical_indication,
            medication.clinical_reasoning,
            medication.monitoring_advice,
            medication.patient_instructions,
        ):
            placeholder = find_placeholder_marker(field_value)
            if placeholder is not None:
                raise HallucinatedMedicationError(medication.generic_name, placeholder)
