"""Unit tests for `PatientEducationWorkflowAdapter` — the only adapter in
this package with two simultaneous prerequisites, and the literal final
step of this task's own WORKFLOW example pipeline."""

from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.infrastructure.module_adapters.patient_education_adapter import (
    PatientEducationWorkflowAdapter,
)
from tests.unit.modules.ai_orchestrator.application.fakes import make_bundle
from tests.unit.modules.ai_orchestrator.infrastructure.module_adapters._peer_fakes import (
    FakePatientEducationAIPort,
    make_generated_patient_education,
)


class TestPatientEducationWorkflowAdapter:
    def test_module_is_patient_education(self) -> None:
        adapter = PatientEducationWorkflowAdapter(facade=FakePatientEducationAIPort())
        assert adapter.module == WorkflowModule.PATIENT_EDUCATION

    def test_check_prerequisites_missing_when_no_diagnoses_or_medications(self) -> None:
        adapter = PatientEducationWorkflowAdapter(facade=FakePatientEducationAIPort())
        reasons = adapter.check_prerequisites(make_bundle())
        assert reasons == ("no diagnoses were provided", "no current medications were provided")

    def test_check_prerequisites_missing_when_only_diagnoses_present(self) -> None:
        adapter = PatientEducationWorkflowAdapter(facade=FakePatientEducationAIPort())
        bundle = make_bundle(diagnoses=("hypertension",))
        assert adapter.check_prerequisites(bundle) == ("no current medications were provided",)

    def test_check_prerequisites_missing_when_only_medications_present(self) -> None:
        adapter = PatientEducationWorkflowAdapter(facade=FakePatientEducationAIPort())
        bundle = make_bundle(medication_list=("lisinopril",))
        assert adapter.check_prerequisites(bundle) == ("no diagnoses were provided",)

    def test_check_prerequisites_ready_when_both_present(self) -> None:
        adapter = PatientEducationWorkflowAdapter(facade=FakePatientEducationAIPort())
        bundle = make_bundle(diagnoses=("hypertension",), medication_list=("lisinopril",))
        assert adapter.check_prerequisites(bundle) == ()

    async def test_execute_chains_every_upstream_module(self) -> None:
        facade = FakePatientEducationAIPort()
        adapter = PatientEducationWorkflowAdapter(facade=facade)
        bundle = make_bundle(diagnoses=("hypertension",), medication_list=("lisinopril",))
        context = {
            WorkflowModule.PRESCRIPTION: "upstream prescription",
            WorkflowModule.DRUG_INTERACTION: "upstream drug interaction",
            WorkflowModule.RISK_STRATIFICATION: "upstream risk stratification",
            WorkflowModule.LAB_INTERPRETATION: "upstream lab",
            WorkflowModule.RADIOLOGY_INTERPRETATION: "upstream radiology",
            WorkflowModule.PATHOLOGY_INTERPRETATION: "upstream pathology",
            WorkflowModule.MEDICAL_REASONING: "upstream reasoning",
            WorkflowModule.DIFFERENTIAL_DIAGNOSIS: "upstream differential diagnosis",
        }

        await adapter.execute(bundle, context)

        input_dto = facade.received[0]
        assert input_dto.prescription_ai_output == "upstream prescription"
        assert input_dto.drug_interaction_ai_output == "upstream drug interaction"
        assert input_dto.risk_stratification_ai_output == "upstream risk stratification"
        assert input_dto.laboratory_interpretation == "upstream lab"
        assert input_dto.radiology_interpretation == "upstream radiology"
        assert input_dto.pathology_interpretation == "upstream pathology"
        assert input_dto.medical_reasoning_context == "upstream reasoning"
        assert input_dto.differential_diagnosis_context == "upstream differential diagnosis"

    async def test_execute_passes_diagnoses_and_medications_through(self) -> None:
        facade = FakePatientEducationAIPort()
        adapter = PatientEducationWorkflowAdapter(facade=facade)
        bundle = make_bundle(diagnoses=("hypertension",), medication_list=("lisinopril",))

        await adapter.execute(bundle, {})

        input_dto = facade.received[0]
        assert input_dto.diagnoses == ("hypertension",)
        assert input_dto.current_medications == ("lisinopril",)

    async def test_execute_returns_completed_step_result_with_confidence(self) -> None:
        facade = FakePatientEducationAIPort(
            generated=make_generated_patient_education(
                raw_text="the patient education", confidence_score=0.7
            )
        )
        adapter = PatientEducationWorkflowAdapter(facade=facade)
        bundle = make_bundle(diagnoses=("hypertension",), medication_list=("lisinopril",))

        result = await adapter.execute(bundle, {})

        assert result.module == WorkflowModule.PATIENT_EDUCATION
        assert result.status == WorkflowStepStatus.COMPLETED
        assert result.summary == "the patient education"
        assert result.confidence_score == 0.7

    async def test_execute_passes_patient_age_and_clinical_notes_through(self) -> None:
        facade = FakePatientEducationAIPort()
        adapter = PatientEducationWorkflowAdapter(facade=facade)
        bundle = make_bundle(
            diagnoses=("hypertension",),
            medication_list=("lisinopril",),
            patient_age=59,
            clinical_notes=("prior note",),
            soap_notes=("prior soap",),
        )

        await adapter.execute(bundle, {})

        input_dto = facade.received[0]
        assert input_dto.patient_age == 59
        assert input_dto.clinical_notes == ("prior note",)
        assert input_dto.soap_notes == ("prior soap",)
