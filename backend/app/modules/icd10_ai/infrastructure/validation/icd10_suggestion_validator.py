"""`DefaultICD10SuggestionValidator` — the one concrete
`ICD10SuggestionValidatorPort` implementation this task ships, per
"VALIDATION — invalid ICD codes, duplicate codes, empty responses,
malformed JSON, hallucinated diagnoses, missing confidence scores"
("malformed JSON" is `ICD10SuggestionParserPort`'s concern — a suggestion
set that reaches this validator already parsed successfully, so only
content-level checks remain here, the same split
`app.modules.soap_note_ai.infrastructure.validation.soap_note_validator
.DefaultSOAPNoteValidator` documents for itself).

Reuses `app.shared.infrastructure.text_processing.placeholder_detection
.find_placeholder_marker` (rule: "Reuse... Shared validation framework...
Avoid duplicate implementations").

Checks run in this order, each a distinct failure mode with its own
domain exception:

1. Zero suggestions -> `EmptyICD10ResponseError`.
2. Any suggestion whose `icd10_code` fails
   `ICD10KnowledgePort.is_valid_format` -> `InvalidICD10CodeError`.
3. Any two suggestions sharing the same normalized `icd10_code` ->
   `DuplicateICD10CodeError`.
4. Any suggestion whose `diagnosis_name`, `clinical_reasoning`, or
   `supporting_evidence` contains a recognized placeholder marker ->
   `HallucinatedDiagnosisError`.
5. Any suggestion whose `confidence_score` is `None` or outside
   `[0.0, 1.0]` -> `MissingConfidenceScoreError`.
"""

from app.modules.icd10_ai.application.ports import ICD10KnowledgePort, ICD10SuggestionValidatorPort
from app.modules.icd10_ai.domain.exceptions import (
    DuplicateICD10CodeError,
    EmptyICD10ResponseError,
    HallucinatedDiagnosisError,
    InvalidICD10CodeError,
    MissingConfidenceScoreError,
)
from app.modules.icd10_ai.domain.value_objects import ICD10Suggestion, ICD10SuggestionSet
from app.shared.infrastructure.text_processing.placeholder_detection import (
    find_placeholder_marker,
)


class DefaultICD10SuggestionValidator(ICD10SuggestionValidatorPort):
    def __init__(self, *, knowledge: ICD10KnowledgePort) -> None:
        self._knowledge = knowledge

    def validate(self, suggestion_set: ICD10SuggestionSet) -> None:
        if suggestion_set.is_empty:
            raise EmptyICD10ResponseError()

        self._check_valid_and_unique_codes(suggestion_set.suggestions)

        for suggestion in suggestion_set.suggestions:
            self._check_no_hallucinated_placeholders(suggestion)

        for suggestion in suggestion_set.suggestions:
            self._check_confidence_score(suggestion)

    def _check_valid_and_unique_codes(self, suggestions: tuple[ICD10Suggestion, ...]) -> None:
        seen_codes: set[str] = set()
        for suggestion in suggestions:
            normalized_code = suggestion.icd10_code.strip().upper()
            if not self._knowledge.is_valid_format(normalized_code):
                raise InvalidICD10CodeError(suggestion.icd10_code)
            if normalized_code in seen_codes:
                raise DuplicateICD10CodeError(suggestion.icd10_code)
            seen_codes.add(normalized_code)

    def _check_no_hallucinated_placeholders(self, suggestion: ICD10Suggestion) -> None:
        for field_value in (
            suggestion.diagnosis_name,
            suggestion.clinical_reasoning,
            suggestion.supporting_evidence,
        ):
            placeholder = find_placeholder_marker(field_value)
            if placeholder is not None:
                raise HallucinatedDiagnosisError(suggestion.icd10_code, placeholder)

    def _check_confidence_score(self, suggestion: ICD10Suggestion) -> None:
        score = suggestion.confidence_score
        if score is None or not (0.0 <= score <= 1.0):
            raise MissingConfidenceScoreError(suggestion.icd10_code)
