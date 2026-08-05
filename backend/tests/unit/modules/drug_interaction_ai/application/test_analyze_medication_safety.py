"""Unit tests for `AnalyzeMedicationSafetyUseCase`."""

from uuid import uuid4

import pytest

from app.modules.drug_interaction_ai.application.services.alternative_medication_service import (
    AlternativeMedicationService,
)
from app.modules.drug_interaction_ai.application.services.contraindication_service import (
    ContraindicationService,
)
from app.modules.drug_interaction_ai.application.services.dose_adjustment_service import (
    DoseAdjustmentService,
)
from app.modules.drug_interaction_ai.application.services.drug_interaction_service import (
    DrugInteractionService,
)
from app.modules.drug_interaction_ai.application.services.medication_safety_service import (
    MedicationSafetyService,
)
from app.modules.drug_interaction_ai.application.use_cases.analyze_medication_safety import (
    AnalyzeMedicationSafetyUseCase,
)
from app.modules.drug_interaction_ai.domain.enums import (
    DrugInteractionOutputFormat,
    DrugInteractionSetting,
    EvidenceLevel,
    SafetyIssueCategory,
    SafetySeverity,
)
from app.modules.drug_interaction_ai.domain.exceptions import (
    HallucinatedInteractionError,
    InvalidDrugInteractionConfidenceValueError,
    InvalidDrugInteractionResponseFormatError,
    MissingInteractionEvidenceError,
    UnknownMedicationError,
)
from app.modules.drug_interaction_ai.domain.value_objects import DrugInteractionAnalysisInput
from tests.unit.modules.drug_interaction_ai.application.fakes import (
    FakeDoseAdjustmentPort,
    FakeDrugInteractionPort,
    FakeDrugSafetyAnalysisAuditLoggerPort,
    FakeDrugSafetyAnalysisGeneratorPort,
    FakeDrugSafetyAnalysisParserPort,
    FakeDrugSafetyAnalysisValidatorPort,
    FakeInteractionEvidencePort,
    FakeMedicalReasoningAIPort,
    FakeMedicationSafetyPort,
    make_generation_session,
    make_issue,
    make_medication,
    make_result,
)


def _input(**overrides: object) -> DrugInteractionAnalysisInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "medication_setting": DrugInteractionSetting.OUTPATIENT,
        "current_medications": (make_medication(),),
    }
    defaults.update(overrides)
    return DrugInteractionAnalysisInput(**defaults)  # type: ignore[arg-type]


def _use_case(
    *,
    generator: FakeDrugSafetyAnalysisGeneratorPort | None = None,
    parser: FakeDrugSafetyAnalysisParserPort | None = None,
    validator: FakeDrugSafetyAnalysisValidatorPort | None = None,
    audit_logger: FakeDrugSafetyAnalysisAuditLoggerPort | None = None,
    drug_interaction_port: FakeDrugInteractionPort | None = None,
    evidence_port: FakeInteractionEvidencePort | None = None,
    medication_safety_port: FakeMedicationSafetyPort | None = None,
    dose_adjustment_port: FakeDoseAdjustmentPort | None = None,
    medical_reasoning: FakeMedicalReasoningAIPort | None = None,
) -> tuple[
    AnalyzeMedicationSafetyUseCase,
    FakeDrugSafetyAnalysisGeneratorPort,
    FakeDrugSafetyAnalysisParserPort,
    FakeDrugSafetyAnalysisValidatorPort,
    FakeDrugSafetyAnalysisAuditLoggerPort,
    FakeMedicalReasoningAIPort,
]:
    generator = generator or FakeDrugSafetyAnalysisGeneratorPort()
    parser = parser or FakeDrugSafetyAnalysisParserPort()
    validator = validator or FakeDrugSafetyAnalysisValidatorPort()
    audit_logger = audit_logger or FakeDrugSafetyAnalysisAuditLoggerPort()
    medical_reasoning = medical_reasoning or FakeMedicalReasoningAIPort()

    use_case = AnalyzeMedicationSafetyUseCase(
        generator=generator,
        parser=parser,
        validator=validator,
        drug_interaction_service=DrugInteractionService(
            interaction_port=drug_interaction_port or FakeDrugInteractionPort(),
            evidence_port=evidence_port or FakeInteractionEvidencePort(),
        ),
        medication_safety_service=MedicationSafetyService(
            port=medication_safety_port or FakeMedicationSafetyPort()
        ),
        contraindication_service=ContraindicationService(
            port=medication_safety_port or FakeMedicationSafetyPort()
        ),
        dose_adjustment_service=DoseAdjustmentService(
            port=dose_adjustment_port or FakeDoseAdjustmentPort()
        ),
        alternative_medication_service=AlternativeMedicationService(),
        medical_reasoning=medical_reasoning,
        audit_logger=audit_logger,
    )
    return use_case, generator, parser, validator, audit_logger, medical_reasoning


class TestAnalyzeMedicationSafetyUseCaseHappyPath:
    async def test_returns_result_and_session(self) -> None:
        use_case, *_ = _use_case()

        generated = await use_case.execute(_input())

        assert generated.result is not None
        assert generated.session is not None

    async def test_calls_generator_then_parser_then_validator_in_order(self) -> None:
        parsed_result = make_result()
        use_case, generator, parser, validator, _audit, _reasoning = _use_case(
            parser=FakeDrugSafetyAnalysisParserPort(result=parsed_result)
        )
        input_dto = _input()

        await use_case.execute(input_dto)

        assert generator.received == [input_dto]
        assert parser.received[0][0] == generator._raw_text
        assert validator.received[0][0] == parsed_result
        assert validator.received[0][1] == input_dto

    async def test_logs_a_generation_session_on_success(self) -> None:
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case()

        await use_case.execute(_input())

        assert len(audit.sessions) == 1
        assert audit.failures == []

    async def test_passes_output_format_through_to_the_parser(self) -> None:
        use_case, _generator, parser, _validator, _audit, _reasoning = _use_case()

        await use_case.execute(_input(output_format=DrugInteractionOutputFormat.MARKDOWN))

        assert parser.received[0][1] is DrugInteractionOutputFormat.MARKDOWN

    async def test_merges_known_interactions_detected_deterministically(self) -> None:
        parsed_result = make_result(interactions=())
        known_issue = make_issue(description="Deterministically detected interaction")
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeDrugSafetyAnalysisParserPort(result=parsed_result),
            drug_interaction_port=FakeDrugInteractionPort(issue=known_issue),
        )
        input_dto = _input(
            current_medications=(
                make_medication(drug_name="Warfarin"),
                make_medication(drug_name="Aspirin"),
            )
        )

        generated = await use_case.execute(input_dto)

        descriptions = {issue.description for issue in generated.result.interactions}
        assert "Deterministically detected interaction" in descriptions

    async def test_merges_patient_context_risks(self) -> None:
        parsed_result = make_result(interactions=())
        context_issue = make_issue(
            category=SafetyIssueCategory.DRUG_ALLERGY_INTERACTION,
            description="Allergy conflict",
        )
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeDrugSafetyAnalysisParserPort(result=parsed_result),
            medication_safety_port=FakeMedicationSafetyPort(context_risks=(context_issue,)),
        )

        generated = await use_case.execute(_input())

        descriptions = {issue.description for issue in generated.result.interactions}
        assert "Allergy conflict" in descriptions

    async def test_merges_pharmacologic_risk_flags(self) -> None:
        parsed_result = make_result(interactions=())
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeDrugSafetyAnalysisParserPort(result=parsed_result),
            medication_safety_port=FakeMedicationSafetyPort(
                risk_flags=(SafetyIssueCategory.BLEEDING_RISK,)
            ),
        )

        generated = await use_case.execute(_input())

        categories = {issue.category for issue in generated.result.interactions}
        assert SafetyIssueCategory.BLEEDING_RISK in categories

    async def test_merges_reconciliation_issues_from_current_medications_only(self) -> None:
        parsed_result = make_result(interactions=())
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeDrugSafetyAnalysisParserPort(result=parsed_result)
        )
        input_dto = _input(
            current_medications=(
                make_medication(drug_name="Warfarin", dose="5mg"),
                make_medication(drug_name="Warfarin", dose="10mg"),
            )
        )

        generated = await use_case.execute(input_dto)

        categories = {issue.category for issue in generated.result.interactions}
        assert SafetyIssueCategory.MEDICATION_RECONCILIATION_ISSUE in categories

    async def test_merges_duplicate_therapy_issues(self) -> None:
        parsed_result = make_result(interactions=())
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeDrugSafetyAnalysisParserPort(result=parsed_result)
        )
        input_dto = _input(
            current_medications=(make_medication(drug_name="Warfarin", dose="5mg"),),
            new_prescription=make_medication(drug_name="Warfarin", dose="10mg"),
        )

        generated = await use_case.execute(input_dto)

        categories = {issue.category for issue in generated.result.interactions}
        assert SafetyIssueCategory.DUPLICATE_THERAPY in categories

    async def test_merges_deterministic_contraindications(self) -> None:
        parsed_result = make_result(contraindications=("Existing contraindication",))
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeDrugSafetyAnalysisParserPort(result=parsed_result),
            medication_safety_port=FakeMedicationSafetyPort(
                contraindication="Deterministic contraindication"
            ),
        )

        generated = await use_case.execute(_input())

        assert "Existing contraindication" in generated.result.contraindications
        assert "Deterministic contraindication" in generated.result.contraindications

    async def test_merges_deterministic_black_box_warnings(self) -> None:
        parsed_result = make_result(warnings=())
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeDrugSafetyAnalysisParserPort(result=parsed_result),
            medication_safety_port=FakeMedicationSafetyPort(
                black_box_warning="Black box warning text"
            ),
        )

        generated = await use_case.execute(_input())

        assert "Black box warning text" in generated.result.warnings

    async def test_merges_deterministic_dose_adjustment_suggestions(self) -> None:
        parsed_result = make_result(dose_adjustment_suggestions=())
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeDrugSafetyAnalysisParserPort(result=parsed_result),
            dose_adjustment_port=FakeDoseAdjustmentPort(suggestion="Reduce dose"),
        )

        generated = await use_case.execute(_input())

        assert "Reduce dose" in generated.result.dose_adjustment_suggestions

    async def test_derives_alternatives_for_high_severity_interactions(self) -> None:
        parsed_result = make_result(
            interactions=(
                make_issue(
                    severity=SafetySeverity.MAJOR,
                    evidence_level=EvidenceLevel.ESTABLISHED,
                    involved_medications=("Warfarin",),
                ),
            ),
            alternative_medication_suggestions=(),
        )
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeDrugSafetyAnalysisParserPort(result=parsed_result)
        )

        generated = await use_case.execute(_input())

        assert len(generated.result.alternative_medication_suggestions) == 1

    async def test_deduplicates_interactions_after_merging(self) -> None:
        issue = make_issue(description="Repeated interaction")
        parsed_result = make_result(interactions=(issue,))
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeDrugSafetyAnalysisParserPort(result=parsed_result),
            drug_interaction_port=FakeDrugInteractionPort(
                issue=make_issue(description="repeated interaction")
            ),
        )
        input_dto = _input(
            current_medications=(
                make_medication(drug_name="Warfarin"),
                make_medication(drug_name="Aspirin"),
            )
        )

        generated = await use_case.execute(input_dto)

        matching = [
            i
            for i in generated.result.interactions
            if i.description.lower() == "repeated interaction"
        ]
        assert len(matching) == 1

    async def test_scores_confidence_via_the_medical_reasoning_facade(self) -> None:
        parsed_result = make_result(confidence_score=None, interactions=())
        reasoning = FakeMedicalReasoningAIPort(confidence_value=0.61)
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeDrugSafetyAnalysisParserPort(result=parsed_result),
            medical_reasoning=reasoning,
        )

        generated = await use_case.execute(_input())

        assert generated.result.confidence_score == 0.61
        call = reasoning.score_confidence_calls[0]
        assert call["ai_reported"] is None
        assert call["contradicting_count"] == 0
        assert call["missing_information_count"] == 0

    async def test_preserves_ai_reported_confidence(self) -> None:
        parsed_result = make_result(confidence_score=0.92, interactions=())
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeDrugSafetyAnalysisParserPort(result=parsed_result)
        )

        generated = await use_case.execute(_input())

        assert generated.result.confidence_score == 0.92

    async def test_new_prescription_is_included_in_interaction_detection(self) -> None:
        parsed_result = make_result(interactions=())
        known_issue = make_issue(description="New prescription interacts")
        use_case, *_rest, _reasoning = _use_case(
            parser=FakeDrugSafetyAnalysisParserPort(result=parsed_result),
            drug_interaction_port=FakeDrugInteractionPort(issue=known_issue),
        )
        input_dto = _input(
            current_medications=(make_medication(drug_name="Warfarin"),),
            new_prescription=make_medication(drug_name="Ibuprofen"),
        )

        generated = await use_case.execute(input_dto)

        descriptions = {issue.description for issue in generated.result.interactions}
        assert "New prescription interacts" in descriptions


class TestAnalyzeMedicationSafetyUseCaseFailureModes:
    async def test_parsing_failure_raises_and_logs_a_failure(self) -> None:
        parser = FakeDrugSafetyAnalysisParserPort(
            error=InvalidDrugInteractionResponseFormatError("malformed JSON")
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(parser=parser)

        with pytest.raises(InvalidDrugInteractionResponseFormatError):
            await use_case.execute(_input())

        assert audit.failures[0]["stage"] == "parse_or_validate"
        assert audit.failures[0]["error_code"] == "InvalidDrugInteractionResponseFormatError"
        assert audit.sessions == []

    async def test_unknown_medication_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeDrugSafetyAnalysisValidatorPort(error=UnknownMedicationError("Ibuprofen"))
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            validator=validator
        )

        with pytest.raises(UnknownMedicationError):
            await use_case.execute(_input())

        assert audit.failures[0]["error_code"] == "UnknownMedicationError"

    async def test_hallucinated_interaction_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeDrugSafetyAnalysisValidatorPort(
            error=HallucinatedInteractionError("safety_summary", "[insert]")
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            validator=validator
        )

        with pytest.raises(HallucinatedInteractionError):
            await use_case.execute(_input())

        assert audit.failures[0]["error_code"] == "HallucinatedInteractionError"

    async def test_invalid_confidence_value_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeDrugSafetyAnalysisValidatorPort(
            error=InvalidDrugInteractionConfidenceValueError()
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            validator=validator
        )

        with pytest.raises(InvalidDrugInteractionConfidenceValueError):
            await use_case.execute(_input())

        assert audit.failures[0]["error_code"] == "InvalidDrugInteractionConfidenceValueError"

    async def test_missing_evidence_failure_raises_and_logs_a_failure(self) -> None:
        validator = FakeDrugSafetyAnalysisValidatorPort(
            error=MissingInteractionEvidenceError("Warfarin and Aspirin")
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            validator=validator
        )

        with pytest.raises(MissingInteractionEvidenceError):
            await use_case.execute(_input())

        assert audit.failures[0]["error_code"] == "MissingInteractionEvidenceError"

    async def test_ai_foundation_errors_from_the_generator_propagate_unwrapped(self) -> None:
        class _FakeFoundationError(Exception):
            pass

        generator = FakeDrugSafetyAnalysisGeneratorPort(error=_FakeFoundationError("provider down"))
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            generator=generator
        )

        with pytest.raises(_FakeFoundationError):
            await use_case.execute(_input())

        assert audit.failures == []
        assert audit.sessions == []

    async def test_generation_id_on_failure_log_matches_the_session_from_the_generator(
        self,
    ) -> None:
        session = make_generation_session()
        generator = FakeDrugSafetyAnalysisGeneratorPort(session=session)
        parser = FakeDrugSafetyAnalysisParserPort(
            error=InvalidDrugInteractionResponseFormatError("x")
        )
        use_case, _generator, _parser, _validator, audit, _reasoning = _use_case(
            generator=generator, parser=parser
        )

        with pytest.raises(InvalidDrugInteractionResponseFormatError):
            await use_case.execute(_input())

        assert audit.failures[0]["generation_id"] == session.generation_id
