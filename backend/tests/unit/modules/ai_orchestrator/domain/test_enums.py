"""Tests for the AI Healthcare Orchestrator module's domain enums —
membership, values, and the string-enum contract."""

import pytest

from app.modules.ai_orchestrator.domain.enums import (
    WorkflowModule,
    WorkflowStatus,
    WorkflowStepStatus,
)


class TestWorkflowModule:
    def test_has_exactly_twelve_members(self) -> None:
        assert len(WorkflowModule) == 12

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (WorkflowModule.CLINICAL_NOTE, "clinical_note"),
            (WorkflowModule.SOAP_NOTE, "soap_note"),
            (WorkflowModule.ICD10_CODING, "icd10_coding"),
            (WorkflowModule.PRESCRIPTION, "prescription"),
            (WorkflowModule.DIFFERENTIAL_DIAGNOSIS, "differential_diagnosis"),
            (WorkflowModule.MEDICAL_REASONING, "medical_reasoning"),
            (WorkflowModule.LAB_INTERPRETATION, "lab_interpretation"),
            (WorkflowModule.RADIOLOGY_INTERPRETATION, "radiology_interpretation"),
            (WorkflowModule.PATHOLOGY_INTERPRETATION, "pathology_interpretation"),
            (WorkflowModule.DRUG_INTERACTION, "drug_interaction"),
            (WorkflowModule.RISK_STRATIFICATION, "risk_stratification"),
            (WorkflowModule.PATIENT_EDUCATION, "patient_education"),
        ],
    )
    def test_member_values(self, member: WorkflowModule, value: str) -> None:
        assert member.value == value

    def test_is_str_subclass(self) -> None:
        assert isinstance(WorkflowModule.CLINICAL_NOTE, str)

    def test_no_foundation_or_copilot_members(self) -> None:
        values = {member.value for member in WorkflowModule}
        assert "ai_foundation" not in values
        assert "clinical_copilot" not in values
        assert "ai_copilot" not in values


class TestWorkflowStepStatus:
    def test_has_exactly_six_members(self) -> None:
        assert len(WorkflowStepStatus) == 6

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (WorkflowStepStatus.PENDING, "pending"),
            (WorkflowStepStatus.RUNNING, "running"),
            (WorkflowStepStatus.COMPLETED, "completed"),
            (WorkflowStepStatus.FAILED, "failed"),
            (WorkflowStepStatus.SKIPPED, "skipped"),
            (WorkflowStepStatus.CANCELLED, "cancelled"),
        ],
    )
    def test_member_values(self, member: WorkflowStepStatus, value: str) -> None:
        assert member.value == value


class TestWorkflowStatus:
    def test_has_exactly_four_members(self) -> None:
        assert len(WorkflowStatus) == 4

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (WorkflowStatus.COMPLETED, "completed"),
            (WorkflowStatus.PARTIALLY_COMPLETED, "partially_completed"),
            (WorkflowStatus.FAILED, "failed"),
            (WorkflowStatus.CANCELLED, "cancelled"),
        ],
    )
    def test_member_values(self, member: WorkflowStatus, value: str) -> None:
        assert member.value == value
