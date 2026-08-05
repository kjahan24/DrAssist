"""Unit tests for `MedicalReasoningWorkflowAdapter`."""

import pytest

from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.infrastructure.module_adapters.medical_reasoning_adapter import (
    MedicalReasoningWorkflowAdapter,
    _average_confidence,
)
from tests.unit.modules.ai_orchestrator.application.fakes import make_bundle
from tests.unit.modules.ai_orchestrator.infrastructure.module_adapters._peer_fakes import (
    FakeMedicalReasoningAIPort,
    make_generated_medical_reasoning,
)


class TestAverageConfidence:
    def test_averages_all_present_scores(self) -> None:
        assert _average_confidence(0.6, 0.8, 1.0) == pytest.approx(0.8)

    def test_skips_none_values(self) -> None:
        assert _average_confidence(0.5, None, None) == 0.5

    def test_returns_none_when_all_none(self) -> None:
        assert _average_confidence(None, None, None) is None


class TestMedicalReasoningWorkflowAdapter:
    def test_module_is_medical_reasoning(self) -> None:
        adapter = MedicalReasoningWorkflowAdapter(facade=FakeMedicalReasoningAIPort())
        assert adapter.module == WorkflowModule.MEDICAL_REASONING

    def test_check_prerequisites_always_ready(self) -> None:
        adapter = MedicalReasoningWorkflowAdapter(facade=FakeMedicalReasoningAIPort())
        assert adapter.check_prerequisites(make_bundle()) == ()

    async def test_execute_falls_back_to_bundle_imaging_findings(self) -> None:
        facade = FakeMedicalReasoningAIPort()
        adapter = MedicalReasoningWorkflowAdapter(facade=facade)
        bundle = make_bundle(radiology_findings=("clear chest",), pathology_findings=("benign",))

        await adapter.execute(bundle, {})

        assert facade.received[0].imaging_summary == "clear chest; benign"

    async def test_execute_prefers_upstream_radiology_over_pathology_and_bundle(self) -> None:
        facade = FakeMedicalReasoningAIPort()
        adapter = MedicalReasoningWorkflowAdapter(facade=facade)
        bundle = make_bundle(radiology_findings=("fallback",))
        context = {
            WorkflowModule.RADIOLOGY_INTERPRETATION: "upstream radiology",
            WorkflowModule.PATHOLOGY_INTERPRETATION: "upstream pathology",
        }

        await adapter.execute(bundle, context)

        assert facade.received[0].imaging_summary == "upstream radiology"

    async def test_execute_falls_back_to_pathology_when_no_radiology(self) -> None:
        facade = FakeMedicalReasoningAIPort()
        adapter = MedicalReasoningWorkflowAdapter(facade=facade)
        context = {WorkflowModule.PATHOLOGY_INTERPRETATION: "upstream pathology"}

        await adapter.execute(make_bundle(), context)

        assert facade.received[0].imaging_summary == "upstream pathology"

    async def test_execute_appends_upstream_clinical_and_soap_notes(self) -> None:
        facade = FakeMedicalReasoningAIPort()
        adapter = MedicalReasoningWorkflowAdapter(facade=facade)
        bundle = make_bundle(clinical_notes=("existing note",), soap_notes=("existing soap",))
        context = {
            WorkflowModule.CLINICAL_NOTE: "upstream clinical note",
            WorkflowModule.SOAP_NOTE: "upstream soap note",
        }

        await adapter.execute(bundle, context)

        evidence = facade.received[0]
        assert evidence.clinical_notes == ("existing note", "upstream clinical note")
        assert evidence.soap_notes == ("existing soap", "upstream soap note")

    async def test_execute_chains_upstream_icd10(self) -> None:
        facade = FakeMedicalReasoningAIPort()
        adapter = MedicalReasoningWorkflowAdapter(facade=facade)
        context = {WorkflowModule.ICD10_CODING: "upstream icd10 codes"}

        await adapter.execute(make_bundle(), context)

        assert facade.received[0].icd10_suggestions == ("upstream icd10 codes",)

    async def test_execute_passes_allergies_and_medications_through(self) -> None:
        facade = FakeMedicalReasoningAIPort()
        adapter = MedicalReasoningWorkflowAdapter(facade=facade)
        bundle = make_bundle(allergies=("latex",), medication_list=("aspirin",))

        await adapter.execute(bundle, {})

        evidence = facade.received[0]
        assert evidence.allergies == ("latex",)
        assert evidence.medications == ("aspirin",)

    async def test_execute_confidence_score_averages_three_peer_fields(self) -> None:
        facade = FakeMedicalReasoningAIPort(
            generated=make_generated_medical_reasoning(
                clinical_confidence=0.6, diagnostic_confidence=0.8, therapeutic_confidence=1.0
            )
        )
        adapter = MedicalReasoningWorkflowAdapter(facade=facade)

        result = await adapter.execute(make_bundle(), {})

        assert result.confidence_score == pytest.approx(0.8)

    async def test_execute_returns_completed_step_result(self) -> None:
        facade = FakeMedicalReasoningAIPort(
            generated=make_generated_medical_reasoning(raw_text="the medical reasoning")
        )
        adapter = MedicalReasoningWorkflowAdapter(facade=facade)

        result = await adapter.execute(make_bundle(), {})

        assert result.module == WorkflowModule.MEDICAL_REASONING
        assert result.status == WorkflowStepStatus.COMPLETED
        assert result.summary == "the medical reasoning"
