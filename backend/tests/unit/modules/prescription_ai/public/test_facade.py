"""Unit tests for `PrescriptionAIFacade` — exercised through
`PrescriptionAIPort` exactly as a future consumer module would call it,
per `docs/backend-architecture/12_testing_architecture.md`'s "Contract
tests" framing."""

from uuid import uuid4

from app.modules.prescription_ai.application.services.medication_safety_analysis_service import (
    MedicationSafetyAnalysisService,
)
from app.modules.prescription_ai.application.services.prescription_suggestion_renderer import (
    PrescriptionSuggestionRenderer,
)
from app.modules.prescription_ai.application.use_cases.analyze_medication_safety import (
    AnalyzeMedicationSafetyUseCase,
)
from app.modules.prescription_ai.application.use_cases.generate_prescription_suggestion import (
    GeneratePrescriptionSuggestionUseCase,
)
from app.modules.prescription_ai.application.use_cases.validate_prescription_context import (
    ValidatePrescriptionContextUseCase,
)
from app.modules.prescription_ai.domain.enums import (
    PrescribingSetting,
    PrescriptionOutputFormat,
    SafetyFindingCategory,
    SafetySeverity,
)
from app.modules.prescription_ai.domain.value_objects import MedicationSafetyFinding
from app.modules.prescription_ai.public.dto import PrescriptionContextInput
from app.modules.prescription_ai.public.facade import PrescriptionAIFacade
from app.modules.prescription_ai.public.interfaces import PrescriptionAIPort
from tests.unit.modules.prescription_ai.application.fakes import (
    FakeDrugInteractionPort,
    FakeMedicationKnowledgePort,
    FakePrescriptionAuditLoggerPort,
    FakePrescriptionGeneratorPort,
    FakePrescriptionSuggestionParserPort,
    FakePrescriptionSuggestionValidatorPort,
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


def _facade(
    *,
    generator: FakePrescriptionGeneratorPort | None = None,
    safety_service: MedicationSafetyAnalysisService | None = None,
) -> PrescriptionAIFacade:
    generator = generator or FakePrescriptionGeneratorPort()
    safety_service = safety_service or MedicationSafetyAnalysisService(
        drug_interaction=FakeDrugInteractionPort(), knowledge=FakeMedicationKnowledgePort()
    )
    generate_use_case = GeneratePrescriptionSuggestionUseCase(
        generator=generator,
        parser=FakePrescriptionSuggestionParserPort(result=make_suggestion_set()),
        validator=FakePrescriptionSuggestionValidatorPort(),
        safety_service=safety_service,
        audit_logger=FakePrescriptionAuditLoggerPort(),
    )
    return PrescriptionAIFacade(
        generate_use_case=generate_use_case,
        validate_use_case=ValidatePrescriptionContextUseCase(),
        analyze_safety_use_case=AnalyzeMedicationSafetyUseCase(safety_service=safety_service),
        renderer=PrescriptionSuggestionRenderer(),
        generator=generator,
    )


class TestPrescriptionAIFacade:
    def test_is_a_prescription_ai_port(self) -> None:
        assert isinstance(_facade(), PrescriptionAIPort)

    async def test_generate_suggestion_delegates_to_the_use_case(self) -> None:
        facade = _facade()

        result = await facade.generate_suggestion(_context())

        assert result.suggestions is not None
        assert result.session is not None

    async def test_stream_generate_suggestion_delegates_to_the_generator(self) -> None:
        generator = FakePrescriptionGeneratorPort(raw_text="hello world")
        facade = _facade(generator=generator)

        chunks = [chunk async for chunk in facade.stream_generate_suggestion(_context())]

        assert "".join(c.delta for c in chunks) == "hello world"

    async def test_analyze_medication_safety_delegates_to_the_use_case(self) -> None:
        finding = MedicationSafetyFinding(
            category=SafetyFindingCategory.DRUG_INTERACTION,
            severity=SafetySeverity.HIGH,
            description="Interaction found",
        )
        safety_service = MedicationSafetyAnalysisService(
            drug_interaction=FakeDrugInteractionPort(interaction_findings=(finding,)),
            knowledge=FakeMedicationKnowledgePort(),
        )
        facade = _facade(safety_service=safety_service)
        suggestion_set = make_suggestion_set()

        findings = await facade.analyze_medication_safety(suggestion_set)

        assert finding in findings

    async def test_render_suggestions_delegates_to_the_renderer(self) -> None:
        facade = _facade()
        suggestion_set = make_suggestion_set()

        rendered = await facade.render_suggestions(
            suggestion_set, target_format=PrescriptionOutputFormat.TEXT
        )

        assert "CLINICAL REASONING:" in rendered

    async def test_validate_context_delegates_to_the_use_case(self) -> None:
        facade = _facade()

        result = await facade.validate_context(_context())

        assert result.is_valid is True
