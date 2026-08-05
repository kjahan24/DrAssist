"""Tests for `GeneratePatientEducationUseCase` — the full generate/
parse/validate/enrich/audit pipeline, exercised against fakes."""

import pytest

from app.modules.patient_education_ai.application.services.discharge_instruction_service import (
    DischargeInstructionService,
)
from app.modules.patient_education_ai.application.services.lifestyle_recommendation_service import (  # noqa: E501
    LifestyleRecommendationService,
)
from app.modules.patient_education_ai.application.services.patient_education_service import (
    PatientEducationService,
)
from app.modules.patient_education_ai.application.use_cases.generate_patient_education import (
    GeneratePatientEducationUseCase,
)
from app.modules.patient_education_ai.domain.exceptions import (
    HallucinatedRecommendationError,
    InvalidPatientEducationResponseFormatError,
    UnsafeInstructionError,
)
from tests.unit.modules.patient_education_ai.application.fakes import (
    FakeDischargeInstructionPort,
    FakeLifestyleRecommendationPort,
    FakeMedicalReasoningAIPort,
    FakePatientEducationAnalysisAuditLoggerPort,
    FakePatientEducationAnalysisGeneratorPort,
    FakePatientEducationAnalysisParserPort,
    FakePatientEducationAnalysisValidatorPort,
    FakePatientEducationPort,
    make_input,
    make_result,
)


def _make_use_case(
    *,
    generator: FakePatientEducationAnalysisGeneratorPort | None = None,
    parser: FakePatientEducationAnalysisParserPort | None = None,
    validator: FakePatientEducationAnalysisValidatorPort | None = None,
    audit_logger: FakePatientEducationAnalysisAuditLoggerPort | None = None,
    medical_reasoning: FakeMedicalReasoningAIPort | None = None,
    education_port: FakePatientEducationPort | None = None,
    discharge_instruction_port: FakeDischargeInstructionPort | None = None,
    lifestyle_recommendation_port: FakeLifestyleRecommendationPort | None = None,
) -> tuple[GeneratePatientEducationUseCase, dict[str, object]]:
    generator = generator or FakePatientEducationAnalysisGeneratorPort()
    parser = parser or FakePatientEducationAnalysisParserPort()
    validator = validator or FakePatientEducationAnalysisValidatorPort()
    audit_logger = audit_logger or FakePatientEducationAnalysisAuditLoggerPort()
    medical_reasoning = medical_reasoning or FakeMedicalReasoningAIPort()
    education_port = education_port or FakePatientEducationPort()
    discharge_instruction_port = discharge_instruction_port or FakeDischargeInstructionPort()
    lifestyle_recommendation_port = (
        lifestyle_recommendation_port or FakeLifestyleRecommendationPort()
    )

    use_case = GeneratePatientEducationUseCase(
        generator=generator,
        parser=parser,
        validator=validator,
        patient_education_service=PatientEducationService(education_port=education_port),
        discharge_instruction_service=DischargeInstructionService(
            discharge_instruction_port=discharge_instruction_port
        ),
        lifestyle_recommendation_service=LifestyleRecommendationService(
            lifestyle_recommendation_port=lifestyle_recommendation_port
        ),
        medical_reasoning=medical_reasoning,
        audit_logger=audit_logger,
    )
    doubles: dict[str, object] = {
        "generator": generator,
        "parser": parser,
        "validator": validator,
        "audit_logger": audit_logger,
        "medical_reasoning": medical_reasoning,
        "education_port": education_port,
        "discharge_instruction_port": discharge_instruction_port,
        "lifestyle_recommendation_port": lifestyle_recommendation_port,
    }
    return use_case, doubles


class TestSuccessfulExecution:
    async def test_returns_generated_result_with_session(self) -> None:
        use_case, doubles = _make_use_case()
        generated = await use_case.execute(make_input())

        generator = doubles["generator"]
        assert isinstance(generator, FakePatientEducationAnalysisGeneratorPort)
        assert generated.session is generator._session

    async def test_logs_generation_on_success(self) -> None:
        use_case, doubles = _make_use_case()
        await use_case.execute(make_input())

        audit_logger = doubles["audit_logger"]
        assert isinstance(audit_logger, FakePatientEducationAnalysisAuditLoggerPort)
        assert len(audit_logger.sessions) == 1
        assert audit_logger.failures == []

    async def test_parser_and_validator_receive_the_generated_text(self) -> None:
        use_case, doubles = _make_use_case(
            generator=FakePatientEducationAnalysisGeneratorPort(raw_text="raw-ai-output")
        )
        await use_case.execute(make_input())

        parser = doubles["parser"]
        assert isinstance(parser, FakePatientEducationAnalysisParserPort)
        assert parser.received[0][0] == "raw-ai-output"


class TestFailureHandling:
    async def test_parser_error_is_logged_and_reraised(self) -> None:
        error = InvalidPatientEducationResponseFormatError("no JSON object found")
        use_case, doubles = _make_use_case(
            parser=FakePatientEducationAnalysisParserPort(error=error)
        )

        with pytest.raises(InvalidPatientEducationResponseFormatError):
            await use_case.execute(make_input())

        audit_logger = doubles["audit_logger"]
        assert isinstance(audit_logger, FakePatientEducationAnalysisAuditLoggerPort)
        assert len(audit_logger.failures) == 1
        assert audit_logger.failures[0]["stage"] == "parse_or_validate"
        assert (
            audit_logger.failures[0]["error_code"] == "InvalidPatientEducationResponseFormatError"
        )

    async def test_validator_hallucination_error_is_logged_and_reraised(self) -> None:
        error = HallucinatedRecommendationError("patient_summary", "[insert]")
        use_case, doubles = _make_use_case(
            validator=FakePatientEducationAnalysisValidatorPort(error=error)
        )

        with pytest.raises(HallucinatedRecommendationError):
            await use_case.execute(make_input())

        audit_logger = doubles["audit_logger"]
        assert isinstance(audit_logger, FakePatientEducationAnalysisAuditLoggerPort)
        assert len(audit_logger.failures) == 1

    async def test_validator_unsafe_instruction_error_is_logged_and_reraised(self) -> None:
        error = UnsafeInstructionError("medication_instructions", "double your dose")
        use_case, doubles = _make_use_case(
            validator=FakePatientEducationAnalysisValidatorPort(error=error)
        )

        with pytest.raises(UnsafeInstructionError):
            await use_case.execute(make_input())

        audit_logger = doubles["audit_logger"]
        assert isinstance(audit_logger, FakePatientEducationAnalysisAuditLoggerPort)
        assert audit_logger.failures[0]["error_code"] == "UnsafeInstructionError"

    async def test_non_domain_generator_errors_propagate_unaudited(self) -> None:
        use_case, doubles = _make_use_case(
            generator=FakePatientEducationAnalysisGeneratorPort(error=RuntimeError("timeout"))
        )

        with pytest.raises(RuntimeError):
            await use_case.execute(make_input())

        audit_logger = doubles["audit_logger"]
        assert isinstance(audit_logger, FakePatientEducationAnalysisAuditLoggerPort)
        assert audit_logger.failures == []
        assert audit_logger.sessions == []


class TestEnrichment:
    async def test_falls_back_to_deterministic_diagnosis_explanation_when_ai_blank(self) -> None:
        education_port = FakePatientEducationPort(explanation="Deterministic explanation.")
        use_case, _ = _make_use_case(
            parser=FakePatientEducationAnalysisParserPort(
                result=make_result(diagnosis_explanation="")
            ),
            education_port=education_port,
        )

        generated = await use_case.execute(make_input())

        assert generated.result.diagnosis_explanation == "Deterministic explanation."

    async def test_preserves_ai_diagnosis_explanation_when_present(self) -> None:
        education_port = FakePatientEducationPort(explanation="Deterministic explanation.")
        use_case, _ = _make_use_case(
            parser=FakePatientEducationAnalysisParserPort(
                result=make_result(diagnosis_explanation="AI explanation.")
            ),
            education_port=education_port,
        )

        generated = await use_case.execute(make_input())

        assert generated.result.diagnosis_explanation == "AI explanation."

    async def test_merges_deterministic_warning_signs(self) -> None:
        education_port = FakePatientEducationPort(warning_signs=("Severe headache",))
        use_case, _ = _make_use_case(education_port=education_port)

        generated = await use_case.execute(make_input())

        assert "Severe headache" in generated.result.warning_signs

    async def test_merges_deterministic_emergency_instructions(self) -> None:
        education_port = FakePatientEducationPort(emergency_symptoms=("Chest pain at rest",))
        use_case, _ = _make_use_case(education_port=education_port)

        generated = await use_case.execute(make_input())

        assert "Chest pain at rest" in generated.result.emergency_instructions

    async def test_merges_deterministic_medication_instructions(self) -> None:
        discharge_port = FakeDischargeInstructionPort(medication_instruction="Take with food.")
        use_case, _ = _make_use_case(discharge_instruction_port=discharge_port)

        generated = await use_case.execute(make_input())

        assert "Take with food." in generated.result.medication_instructions

    async def test_merges_deterministic_home_care_plan(self) -> None:
        discharge_port = FakeDischargeInstructionPort(home_care_instructions=("Rest and hydrate.",))
        use_case, _ = _make_use_case(discharge_instruction_port=discharge_port)

        generated = await use_case.execute(make_input())

        assert "Rest and hydrate." in generated.result.home_care_plan

    async def test_merges_deterministic_patient_checklist(self) -> None:
        discharge_port = FakeDischargeInstructionPort(
            discharge_checklist=("Fill your prescriptions.",)
        )
        use_case, _ = _make_use_case(discharge_instruction_port=discharge_port)

        generated = await use_case.execute(make_input())

        assert "Fill your prescriptions." in generated.result.patient_checklist

    async def test_merges_deterministic_lifestyle_advice(self) -> None:
        lifestyle_port = FakeLifestyleRecommendationPort(lifestyle=("Limit alcohol.",))
        use_case, _ = _make_use_case(lifestyle_recommendation_port=lifestyle_port)

        generated = await use_case.execute(make_input())

        assert "Limit alcohol." in generated.result.lifestyle_advice

    async def test_merges_deterministic_diet_advice(self) -> None:
        lifestyle_port = FakeLifestyleRecommendationPort(diet=("Low-sodium diet.",))
        use_case, _ = _make_use_case(lifestyle_recommendation_port=lifestyle_port)

        generated = await use_case.execute(make_input())

        assert "Low-sodium diet." in generated.result.diet_advice

    async def test_merges_deterministic_exercise_advice(self) -> None:
        lifestyle_port = FakeLifestyleRecommendationPort(exercise=("Moderate aerobic activity.",))
        use_case, _ = _make_use_case(lifestyle_recommendation_port=lifestyle_port)

        generated = await use_case.execute(make_input())

        assert "Moderate aerobic activity." in generated.result.exercise_advice

    async def test_merges_preventive_care_recommendations_into_follow_up_plan(self) -> None:
        lifestyle_port = FakeLifestyleRecommendationPort(preventive_care=("Annual eye exam.",))
        use_case, _ = _make_use_case(lifestyle_recommendation_port=lifestyle_port)

        generated = await use_case.execute(make_input())

        assert "Annual eye exam." in generated.result.follow_up_plan

    async def test_confidence_score_delegates_to_medical_reasoning_port(self) -> None:
        medical_reasoning = FakeMedicalReasoningAIPort(confidence_value=0.42)
        use_case, _ = _make_use_case(
            parser=FakePatientEducationAnalysisParserPort(
                result=make_result(confidence_score=None)
            ),
            medical_reasoning=medical_reasoning,
        )

        generated = await use_case.execute(make_input())

        assert generated.result.confidence_score == 0.42
        assert len(medical_reasoning.score_confidence_calls) == 1

    async def test_confidence_score_uses_ai_reported_value_when_present(self) -> None:
        use_case, _ = _make_use_case(
            parser=FakePatientEducationAnalysisParserPort(result=make_result(confidence_score=0.9)),
        )

        generated = await use_case.execute(make_input())

        assert generated.result.confidence_score == 0.9
