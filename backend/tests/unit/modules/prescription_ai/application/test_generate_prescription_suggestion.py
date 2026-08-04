"""Unit tests for `GeneratePrescriptionSuggestionUseCase`."""

from uuid import uuid4

import pytest

from app.modules.prescription_ai.application.services.medication_safety_analysis_service import (
    MedicationSafetyAnalysisService,
)
from app.modules.prescription_ai.application.use_cases.generate_prescription_suggestion import (
    GeneratePrescriptionSuggestionUseCase,
)
from app.modules.prescription_ai.domain.enums import (
    PrescribingSetting,
    PrescriptionOutputFormat,
    SafetyFindingCategory,
    SafetySeverity,
)
from app.modules.prescription_ai.domain.exceptions import (
    EmptyPrescriptionResponseError,
    HallucinatedMedicationError,
    InvalidPrescriptionResponseFormatError,
    MissingMedicationDosageError,
)
from app.modules.prescription_ai.domain.value_objects import (
    MedicationSafetyFinding,
    PrescriptionContextInput,
)
from tests.unit.modules.prescription_ai.application.fakes import (
    FakeDrugInteractionPort,
    FakeMedicationKnowledgePort,
    FakePrescriptionAuditLoggerPort,
    FakePrescriptionGeneratorPort,
    FakePrescriptionSuggestionParserPort,
    FakePrescriptionSuggestionValidatorPort,
    make_generation_session,
    make_suggestion_set,
)


def _context(**overrides: object) -> PrescriptionContextInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Sore throat",
        "prescribing_setting": PrescribingSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return PrescriptionContextInput(**defaults)  # type: ignore[arg-type]


def _use_case(
    *,
    generator: FakePrescriptionGeneratorPort | None = None,
    parser: FakePrescriptionSuggestionParserPort | None = None,
    validator: FakePrescriptionSuggestionValidatorPort | None = None,
    audit_logger: FakePrescriptionAuditLoggerPort | None = None,
    safety_service: MedicationSafetyAnalysisService | None = None,
) -> tuple[
    GeneratePrescriptionSuggestionUseCase,
    FakePrescriptionGeneratorPort,
    FakePrescriptionSuggestionParserPort,
    FakePrescriptionSuggestionValidatorPort,
    FakePrescriptionAuditLoggerPort,
]:
    generator = generator or FakePrescriptionGeneratorPort()
    parser = parser or FakePrescriptionSuggestionParserPort()
    validator = validator or FakePrescriptionSuggestionValidatorPort()
    audit_logger = audit_logger or FakePrescriptionAuditLoggerPort()
    safety_service = safety_service or MedicationSafetyAnalysisService(
        drug_interaction=FakeDrugInteractionPort(), knowledge=FakeMedicationKnowledgePort()
    )
    use_case = GeneratePrescriptionSuggestionUseCase(
        generator=generator,
        parser=parser,
        validator=validator,
        safety_service=safety_service,
        audit_logger=audit_logger,
    )
    return use_case, generator, parser, validator, audit_logger


class TestGeneratePrescriptionSuggestionUseCaseHappyPath:
    async def test_returns_suggestions_and_session(self) -> None:
        use_case, *_ = _use_case()

        result = await use_case.execute(_context())

        assert result.suggestions is not None
        assert result.session is not None

    async def test_calls_generator_then_parser_then_validator_in_order(self) -> None:
        suggestion_set = make_suggestion_set()
        use_case, generator, parser, validator, _audit = _use_case(
            parser=FakePrescriptionSuggestionParserPort(result=suggestion_set)
        )
        context = _context()

        result = await use_case.execute(context)

        assert generator.received_contexts == [context]
        assert parser.received[0][0] == generator._raw_text
        assert validator.received == [suggestion_set]
        assert result.suggestions.medications == suggestion_set.medications

    async def test_logs_a_generation_session_on_success(self) -> None:
        use_case, _generator, _parser, _validator, audit = _use_case()

        await use_case.execute(_context())

        assert len(audit.sessions) == 1
        assert audit.failures == []

    async def test_passes_output_format_through_to_the_parser(self) -> None:
        use_case, _generator, parser, _validator, _audit = _use_case()

        await use_case.execute(_context(output_format=PrescriptionOutputFormat.MARKDOWN))

        assert parser.received[0][1] is PrescriptionOutputFormat.MARKDOWN

    async def test_enriches_result_with_deterministic_safety_findings(self) -> None:
        deterministic_finding = MedicationSafetyFinding(
            category=SafetyFindingCategory.DRUG_INTERACTION,
            severity=SafetySeverity.HIGH,
            description="Deterministic finding",
            affected_medications=("amoxicillin", "warfarin"),
        )
        safety_service = MedicationSafetyAnalysisService(
            drug_interaction=FakeDrugInteractionPort(interaction_findings=(deterministic_finding,)),
            knowledge=FakeMedicationKnowledgePort(),
        )
        use_case, *_ = _use_case(safety_service=safety_service)

        result = await use_case.execute(_context())

        assert deterministic_finding in result.suggestions.safety_findings

    async def test_merges_ai_reported_and_deterministic_findings_without_exact_duplicates(
        self,
    ) -> None:
        shared_finding = MedicationSafetyFinding(
            category=SafetyFindingCategory.DRUG_INTERACTION,
            severity=SafetySeverity.HIGH,
            description="Same finding text",
            affected_medications=("amoxicillin", "warfarin"),
        )
        suggestion_set = make_suggestion_set(safety_findings=(shared_finding,))
        safety_service = MedicationSafetyAnalysisService(
            drug_interaction=FakeDrugInteractionPort(interaction_findings=(shared_finding,)),
            knowledge=FakeMedicationKnowledgePort(),
        )
        use_case, *_ = _use_case(
            parser=FakePrescriptionSuggestionParserPort(result=suggestion_set),
            safety_service=safety_service,
        )

        result = await use_case.execute(_context())

        assert result.suggestions.safety_findings.count(shared_finding) == 1


class TestGeneratePrescriptionSuggestionUseCaseFailureModes:
    async def test_parsing_failure_raises_and_logs_a_failure(self) -> None:
        parser = FakePrescriptionSuggestionParserPort(
            error=InvalidPrescriptionResponseFormatError("malformed JSON")
        )
        use_case, _generator, _parser, _validator, audit = _use_case(parser=parser)

        with pytest.raises(InvalidPrescriptionResponseFormatError):
            await use_case.execute(_context())

        assert audit.failures[0]["stage"] == "parse_or_validate"
        assert audit.failures[0]["error_code"] == "InvalidPrescriptionResponseFormatError"
        assert audit.sessions == []

    async def test_empty_response_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakePrescriptionSuggestionValidatorPort(error=EmptyPrescriptionResponseError())
        use_case, _generator, _parser, _validator, audit = _use_case(validator=validator)

        with pytest.raises(EmptyPrescriptionResponseError):
            await use_case.execute(_context())

        assert audit.failures[0]["error_code"] == "EmptyPrescriptionResponseError"

    async def test_missing_dosage_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakePrescriptionSuggestionValidatorPort(
            error=MissingMedicationDosageError("amoxicillin")
        )
        use_case, _generator, _parser, _validator, audit = _use_case(validator=validator)

        with pytest.raises(MissingMedicationDosageError):
            await use_case.execute(_context())

        assert audit.failures[0]["error_code"] == "MissingMedicationDosageError"

    async def test_hallucinated_medication_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakePrescriptionSuggestionValidatorPort(
            error=HallucinatedMedicationError("amoxicillin", "[INSERT]")
        )
        use_case, _generator, _parser, _validator, audit = _use_case(validator=validator)

        with pytest.raises(HallucinatedMedicationError):
            await use_case.execute(_context())

        assert audit.failures[0]["error_code"] == "HallucinatedMedicationError"

    async def test_ai_foundation_errors_from_the_generator_propagate_unwrapped(self) -> None:
        class _FakeFoundationError(Exception):
            pass

        generator = FakePrescriptionGeneratorPort(error=_FakeFoundationError("provider down"))
        use_case, _generator, _parser, _validator, audit = _use_case(generator=generator)

        with pytest.raises(_FakeFoundationError):
            await use_case.execute(_context())

        # This module does not catch/log AI-Foundation-originated errors —
        # no failure record is expected here (see the use case's own
        # module docstring).
        assert audit.failures == []
        assert audit.sessions == []

    async def test_generation_id_on_failure_log_matches_the_session_from_the_generator(
        self,
    ) -> None:
        session = make_generation_session()
        generator = FakePrescriptionGeneratorPort(session=session)
        parser = FakePrescriptionSuggestionParserPort(
            error=InvalidPrescriptionResponseFormatError("x")
        )
        use_case, _generator, _parser, _validator, audit = _use_case(
            generator=generator, parser=parser
        )

        with pytest.raises(InvalidPrescriptionResponseFormatError):
            await use_case.execute(_context())

        assert audit.failures[0]["generation_id"] == session.generation_id
