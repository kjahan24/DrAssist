"""`DefaultLabInterpretationValidator` — the one concrete
`LabInterpretationValidatorPort` implementation this task ships, per this
task's own "missing reasoning, hallucinated values" VALIDATION categories
("malformed AI output" is `LabInterpretationParserPort`'s concern — a
result that reaches this validator already parsed successfully, so only
content-level checks remain here; "malformed lab data"/"duplicate
values"/"impossible numeric ranges"/"invalid units" are all input-side
checks already performed by `domain/value_objects.py`'s own
`__post_init__` before generation ever happens — see `domain
/exceptions.py`'s own module docstring for the full seven-category
mapping).

This task's own VALIDATION list does not name an "empty outputs"
category the way `app.modules.medical_reasoning_ai`'s own task did — a
fully vacuous result is instead caught as the first, most fundamental
case of "missing reasoning" below (a blank `overall_interpretation` is
both), rather than introducing a separate, unrequested exception type.

Reuses `app.shared.infrastructure.text_processing.placeholder_detection
.find_placeholder_marker` (rule: "Reuse... Shared validator... Avoid
duplicate implementations").

Checks run in this order, each a distinct failure mode with its own
domain exception:

1. A blank `overall_interpretation`, or a blank `clinical_significance`
   while findings/evidence/causes/recommendations/warnings were reported
   (a clinical explanation is expected wherever there is something to
   explain) -> `MissingLabReasoningError`.
2. Any hallucinated placeholder in `overall_interpretation`,
   `clinical_significance`, or any finding/evidence/cause/recommendation/
   warning text -> `HallucinatedLabValueError`.
"""

from app.modules.lab_interpretation_ai.application.ports import LabInterpretationValidatorPort
from app.modules.lab_interpretation_ai.domain.exceptions import (
    HallucinatedLabValueError,
    MissingLabReasoningError,
)
from app.modules.lab_interpretation_ai.domain.value_objects import LabInterpretationResult
from app.shared.infrastructure.text_processing.placeholder_detection import (
    find_placeholder_marker,
)


class DefaultLabInterpretationValidator(LabInterpretationValidatorPort):
    def validate(self, result: LabInterpretationResult) -> None:
        self._check_missing_reasoning(result)
        self._check_hallucinated_placeholders(result)

    def _check_missing_reasoning(self, result: LabInterpretationResult) -> None:
        if not result.overall_interpretation.strip():
            raise MissingLabReasoningError("overall_interpretation must not be blank")

        has_supporting_content = bool(
            result.findings
            or result.supporting_evidence
            or result.potential_causes
            or result.suggested_follow_up_tests
            or result.monitoring_recommendations
            or result.red_flag_warnings
        )
        if has_supporting_content and not result.clinical_significance.strip():
            raise MissingLabReasoningError(
                "clinical_significance must not be blank when findings or recommendations "
                "were reported"
            )

    def _check_hallucinated_placeholders(self, result: LabInterpretationResult) -> None:
        text_fields = (
            ("overall_interpretation", result.overall_interpretation),
            ("clinical_significance", result.clinical_significance),
        )
        for field_name, text in text_fields:
            placeholder = find_placeholder_marker(text)
            if placeholder is not None:
                raise HallucinatedLabValueError(field_name, placeholder)

        for finding in result.findings:
            placeholder = find_placeholder_marker(finding.test_name) or find_placeholder_marker(
                finding.value
            )
            if placeholder is not None:
                raise HallucinatedLabValueError("findings", placeholder)

        list_fields = (
            ("supporting_evidence", result.supporting_evidence),
            ("potential_causes", result.potential_causes),
            ("suggested_follow_up_tests", result.suggested_follow_up_tests),
            ("monitoring_recommendations", result.monitoring_recommendations),
            ("red_flag_warnings", result.red_flag_warnings),
        )
        for field_name, items in list_fields:
            for text in items:
                placeholder = find_placeholder_marker(text)
                if placeholder is not None:
                    raise HallucinatedLabValueError(field_name, placeholder)
