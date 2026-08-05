"""Unit tests for `DifferentialDiagnosisWorkflowAdapter`."""

from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.infrastructure.module_adapters.differential_diagnosis_adapter import (  # noqa: E501
    DifferentialDiagnosisWorkflowAdapter,
)
from app.modules.differential_diagnosis_ai.public.dto import (
    DifferentialDiagnosisCandidate,
    DifferentialDiagnosisResult,
    DifferentialOutputFormat,
    GeneratedDifferentialDiagnosis,
    UrgencyLevel,
)
from tests.unit.modules.ai_orchestrator.application.fakes import make_bundle
from tests.unit.modules.ai_orchestrator.infrastructure.module_adapters._peer_fakes import (
    FakeDifferentialDiagnosisAIPort,
    make_generated_differential_diagnosis,
)


def _generated_with_candidates(
    *candidates: DifferentialDiagnosisCandidate,
) -> GeneratedDifferentialDiagnosis:
    base = make_generated_differential_diagnosis()
    return GeneratedDifferentialDiagnosis(
        result=DifferentialDiagnosisResult(
            candidates=candidates,
            serious_diagnoses_not_to_miss=(),
            suggested_investigations=(),
            suggested_referrals=(),
            raw_text=base.result.raw_text,
            output_format=DifferentialOutputFormat.JSON,
        ),
        session=base.session,
    )


class TestDifferentialDiagnosisWorkflowAdapter:
    def test_module_is_differential_diagnosis(self) -> None:
        adapter = DifferentialDiagnosisWorkflowAdapter(facade=FakeDifferentialDiagnosisAIPort())
        assert adapter.module == WorkflowModule.DIFFERENTIAL_DIAGNOSIS

    def test_check_prerequisites_always_ready(self) -> None:
        adapter = DifferentialDiagnosisWorkflowAdapter(facade=FakeDifferentialDiagnosisAIPort())
        assert adapter.check_prerequisites(make_bundle()) == ()

    async def test_execute_falls_back_to_bundle_radiology_findings(self) -> None:
        facade = FakeDifferentialDiagnosisAIPort()
        adapter = DifferentialDiagnosisWorkflowAdapter(facade=facade)
        bundle = make_bundle(radiology_findings=("chest x-ray clear",))

        await adapter.execute(bundle, {})

        assert facade.received[0].imaging_summary == "chest x-ray clear"

    async def test_execute_prefers_upstream_radiology_interpretation(self) -> None:
        facade = FakeDifferentialDiagnosisAIPort()
        adapter = DifferentialDiagnosisWorkflowAdapter(facade=facade)
        bundle = make_bundle(radiology_findings=("fallback finding",))
        context = {WorkflowModule.RADIOLOGY_INTERPRETATION: "upstream radiology interpretation"}

        await adapter.execute(bundle, context)

        assert facade.received[0].imaging_summary == "upstream radiology interpretation"

    async def test_execute_chains_upstream_clinical_note_soap_note_and_icd10(self) -> None:
        facade = FakeDifferentialDiagnosisAIPort()
        adapter = DifferentialDiagnosisWorkflowAdapter(facade=facade)
        context = {
            WorkflowModule.CLINICAL_NOTE: "upstream clinical note",
            WorkflowModule.SOAP_NOTE: "upstream soap note",
            WorkflowModule.ICD10_CODING: "upstream icd10 codes",
        }

        await adapter.execute(make_bundle(), context)

        evidence = facade.received[0]
        assert evidence.clinical_note == "upstream clinical note"
        assert evidence.soap_note == "upstream soap note"
        assert evidence.icd10_suggestions == ("upstream icd10 codes",)

    async def test_execute_passes_patient_age_and_allergies_through(self) -> None:
        facade = FakeDifferentialDiagnosisAIPort()
        adapter = DifferentialDiagnosisWorkflowAdapter(facade=facade)
        bundle = make_bundle(patient_age=33, allergies=("penicillin",))

        await adapter.execute(bundle, {})

        evidence = facade.received[0]
        assert evidence.patient_age == 33
        assert evidence.allergies == ("penicillin",)

    async def test_execute_confidence_score_reads_top_ranked_candidate(self) -> None:
        top_candidate = DifferentialDiagnosisCandidate(
            disease_name="pneumonia",
            icd10_code=None,
            confidence_score=0.42,
            clinical_reasoning="reasoning",
            supporting_findings=(),
            findings_against=(),
            recommended_next_tests=(),
            red_flag_indicators=(),
            urgency_level=UrgencyLevel.ROUTINE,
        )
        facade = FakeDifferentialDiagnosisAIPort(
            generated=_generated_with_candidates(top_candidate)
        )
        adapter = DifferentialDiagnosisWorkflowAdapter(facade=facade)

        result = await adapter.execute(make_bundle(), {})

        assert result.confidence_score == 0.42

    async def test_execute_confidence_score_is_none_when_no_candidates(self) -> None:
        facade = FakeDifferentialDiagnosisAIPort(generated=_generated_with_candidates())
        adapter = DifferentialDiagnosisWorkflowAdapter(facade=facade)

        result = await adapter.execute(make_bundle(), {})

        assert result.confidence_score is None

    async def test_execute_returns_completed_step_result(self) -> None:
        facade = FakeDifferentialDiagnosisAIPort(
            generated=make_generated_differential_diagnosis(raw_text="the differential diagnosis")
        )
        adapter = DifferentialDiagnosisWorkflowAdapter(facade=facade)

        result = await adapter.execute(make_bundle(), {})

        assert result.module == WorkflowModule.DIFFERENTIAL_DIAGNOSIS
        assert result.status == WorkflowStepStatus.COMPLETED
        assert result.summary == "the differential diagnosis"
