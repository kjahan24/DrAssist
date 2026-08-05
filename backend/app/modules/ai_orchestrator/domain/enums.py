"""Enums owned by the AI Healthcare Orchestrator module's domain."""

from enum import StrEnum


class WorkflowModule(StrEnum):
    """The closed vocabulary of orchestratable AI modules — twelve of
    the fourteen modules this task's own ORCHESTRATE section names.

    "AI Foundation" and "AI Clinical Copilot" are deliberately **not**
    members here — see `container.py`'s own module docstring for the
    full reasoning: both are the orchestration *substrate* every module
    (including this one) is already built on, not independently-
    executable content-generating workflow steps with a `Generated*`
    result of their own the way these twelve are.
    """

    CLINICAL_NOTE = "clinical_note"
    SOAP_NOTE = "soap_note"
    ICD10_CODING = "icd10_coding"
    PRESCRIPTION = "prescription"
    DIFFERENTIAL_DIAGNOSIS = "differential_diagnosis"
    MEDICAL_REASONING = "medical_reasoning"
    LAB_INTERPRETATION = "lab_interpretation"
    RADIOLOGY_INTERPRETATION = "radiology_interpretation"
    PATHOLOGY_INTERPRETATION = "pathology_interpretation"
    DRUG_INTERACTION = "drug_interaction"
    RISK_STRATIFICATION = "risk_stratification"
    PATIENT_EDUCATION = "patient_education"


class WorkflowStepStatus(StrEnum):
    """The lifecycle a single step within one workflow execution passes
    through."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class WorkflowStatus(StrEnum):
    """The overall outcome of one workflow execution, per this task's
    own "Support partial execution" requirement: `PARTIALLY_COMPLETED`
    is a first-class, expected outcome, not an error state."""

    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
