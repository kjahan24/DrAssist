"""Unit tests for `DrugInteractionAIFacade` — exercised through
`DrugInteractionAIPort` exactly as a future consumer module would call
it, per `docs/backend-architecture/12_testing_architecture.md`'s
"Contract tests" framing."""

from uuid import uuid4

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
from app.modules.drug_interaction_ai.application.services.drug_safety_report_renderer import (
    DrugSafetyReportRenderer,
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
)
from app.modules.drug_interaction_ai.public.dto import DrugInteractionAnalysisInput
from app.modules.drug_interaction_ai.public.facade import DrugInteractionAIFacade
from app.modules.drug_interaction_ai.public.interfaces import DrugInteractionAIPort
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


def _facade(
    *, generator: FakeDrugSafetyAnalysisGeneratorPort | None = None
) -> DrugInteractionAIFacade:
    generator = generator or FakeDrugSafetyAnalysisGeneratorPort()
    analyze_use_case = AnalyzeMedicationSafetyUseCase(
        generator=generator,
        parser=FakeDrugSafetyAnalysisParserPort(result=make_result()),
        validator=FakeDrugSafetyAnalysisValidatorPort(),
        drug_interaction_service=DrugInteractionService(
            interaction_port=FakeDrugInteractionPort(),
            evidence_port=FakeInteractionEvidencePort(),
        ),
        medication_safety_service=MedicationSafetyService(port=FakeMedicationSafetyPort()),
        contraindication_service=ContraindicationService(port=FakeMedicationSafetyPort()),
        dose_adjustment_service=DoseAdjustmentService(port=FakeDoseAdjustmentPort()),
        alternative_medication_service=AlternativeMedicationService(),
        medical_reasoning=FakeMedicalReasoningAIPort(),
        audit_logger=FakeDrugSafetyAnalysisAuditLoggerPort(),
    )
    return DrugInteractionAIFacade(
        analyze_use_case=analyze_use_case,
        renderer=DrugSafetyReportRenderer(),
        generator=generator,
    )


class TestDrugInteractionAIFacade:
    def test_is_a_drug_interaction_ai_port(self) -> None:
        assert isinstance(_facade(), DrugInteractionAIPort)

    async def test_analyze_medication_safety_delegates_to_the_use_case(self) -> None:
        facade = _facade()

        generated = await facade.analyze_medication_safety(_input())

        assert generated.result is not None
        assert generated.session is not None

    async def test_stream_analyze_medication_safety_delegates_to_the_generator(self) -> None:
        generator = FakeDrugSafetyAnalysisGeneratorPort(raw_text="hello world")
        facade = _facade(generator=generator)

        chunks = [chunk async for chunk in facade.stream_analyze_medication_safety(_input())]

        assert "".join(c.delta for c in chunks) == "hello world"

    async def test_render_result_delegates_to_the_renderer(self) -> None:
        facade = _facade()
        result = make_result()

        rendered = await facade.render_result(
            result, target_format=DrugInteractionOutputFormat.TEXT
        )

        assert "MEDICATION SAFETY SUMMARY:" in rendered
