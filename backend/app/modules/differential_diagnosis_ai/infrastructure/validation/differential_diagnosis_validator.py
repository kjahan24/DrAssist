"""`DefaultDifferentialDiagnosisValidator` — the one concrete
`DifferentialDiagnosisValidatorPort` implementation this task ships, per
"VALIDATION — duplicate diagnoses, empty outputs, malformed JSON,
hallucinated diagnoses, invalid confidence scores, invalid ranking,
inconsistent reasoning" ("malformed JSON" is
`DifferentialDiagnosisParserPort`'s concern — a result that reaches this
validator already parsed successfully, so only content-level checks
remain here, the same split
`app.modules.prescription_ai.infrastructure.validation
.prescription_suggestion_validator.DefaultPrescriptionSuggestionValidator`
documents for itself).

Reuses `app.shared.infrastructure.text_processing.placeholder_detection
.find_placeholder_marker` (rule: "Reuse... Shared validation framework...
Avoid duplicate implementations").

Checks run in this order, each a distinct failure mode with its own
domain exception:

1. Zero candidates -> `EmptyDifferentialResponseError`.
2. Any two candidates sharing the same normalized `disease_name` ->
   `DuplicateDiagnosisError`.
3. Any candidate whose `confidence_score` is `None` or outside
   `[0.0, 1.0]` -> `InvalidConfidenceScoreError` — checked *before*
   ranking (4) since a valid ranking check requires every score to
   already be a trustworthy number.
4. The AI's own returned `candidates` order is not non-increasing by
   `confidence_score` -> `InvalidRankingError`. This is this task's own
   "invalid ranking" category applied to the AI's *self-reported* order
   — independent of, and checked before,
   `application/services/differential_diagnosis_ranking_service
   .DifferentialDiagnosisRankingService`'s own deterministic re-sort
   (which always runs regardless, as the pipeline's canonical ordering
   step) — a badly-out-of-order response is itself a sign of confused or
   unreliable output worth rejecting outright rather than silently
   "fixing".
5. Any candidate whose `disease_name`, `clinical_reasoning`, or any
   `supporting_findings`/`findings_against`/`recommended_next_tests`/
   `red_flag_indicators` entry contains a recognized placeholder marker
   -> `HallucinatedDiagnosisError`.
6. Any candidate whose `supporting_findings` and `findings_against`
   share an identical (normalized) entry -> `InconsistentReasoningError`
   — this task's own "inconsistent reasoning" category: the same finding
   cannot simultaneously support *and* contradict a diagnosis.
"""

from app.modules.differential_diagnosis_ai.application.ports import (
    DifferentialDiagnosisValidatorPort,
)
from app.modules.differential_diagnosis_ai.domain.exceptions import (
    DuplicateDiagnosisError,
    EmptyDifferentialResponseError,
    HallucinatedDiagnosisError,
    InconsistentReasoningError,
    InvalidConfidenceScoreError,
    InvalidRankingError,
)
from app.modules.differential_diagnosis_ai.domain.value_objects import (
    DifferentialDiagnosisCandidate,
    DifferentialDiagnosisResult,
)
from app.shared.infrastructure.text_processing.placeholder_detection import (
    find_placeholder_marker,
)


class DefaultDifferentialDiagnosisValidator(DifferentialDiagnosisValidatorPort):
    def validate(self, result: DifferentialDiagnosisResult) -> None:
        if result.is_empty:
            raise EmptyDifferentialResponseError()

        self._check_duplicates(result.candidates)

        for candidate in result.candidates:
            self._check_confidence_score(candidate)

        self._check_ranking_order(result.candidates)

        for candidate in result.candidates:
            self._check_no_hallucinated_placeholders(candidate)

        for candidate in result.candidates:
            self._check_consistent_reasoning(candidate)

    def _check_duplicates(self, candidates: tuple[DifferentialDiagnosisCandidate, ...]) -> None:
        seen_names: set[str] = set()
        for candidate in candidates:
            normalized = candidate.disease_name.strip().lower()
            if normalized in seen_names:
                raise DuplicateDiagnosisError(candidate.disease_name)
            seen_names.add(normalized)

    def _check_confidence_score(self, candidate: DifferentialDiagnosisCandidate) -> None:
        score = candidate.confidence_score
        if score is None or not (0.0 <= score <= 1.0):
            raise InvalidConfidenceScoreError(candidate.disease_name)

    def _check_ranking_order(self, candidates: tuple[DifferentialDiagnosisCandidate, ...]) -> None:
        scores = [candidate.confidence_score for candidate in candidates]
        for earlier, later in zip(scores, scores[1:], strict=False):
            if earlier is not None and later is not None and later > earlier:
                raise InvalidRankingError(
                    "candidates must be returned in non-increasing confidence order"
                )

    def _check_no_hallucinated_placeholders(
        self, candidate: DifferentialDiagnosisCandidate
    ) -> None:
        text_fields = (candidate.disease_name, candidate.clinical_reasoning)
        list_fields = (
            candidate.supporting_findings,
            candidate.findings_against,
            candidate.recommended_next_tests,
            candidate.red_flag_indicators,
        )
        for field_value in text_fields:
            placeholder = find_placeholder_marker(field_value)
            if placeholder is not None:
                raise HallucinatedDiagnosisError(candidate.disease_name, placeholder)
        for items in list_fields:
            for item in items:
                placeholder = find_placeholder_marker(item)
                if placeholder is not None:
                    raise HallucinatedDiagnosisError(candidate.disease_name, placeholder)

    def _check_consistent_reasoning(self, candidate: DifferentialDiagnosisCandidate) -> None:
        supporting = {finding.strip().lower() for finding in candidate.supporting_findings}
        against = {finding.strip().lower() for finding in candidate.findings_against}
        overlap = supporting & against
        if overlap:
            raise InconsistentReasoningError(
                candidate.disease_name,
                f"{sorted(overlap)[0]!r} appears in both supporting and contradicting findings",
            )
