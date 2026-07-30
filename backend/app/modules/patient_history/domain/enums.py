from enum import StrEnum


class HistoryType(StrEnum):
    ENCOUNTER = "encounter"
    DIAGNOSIS = "diagnosis"
    MEDICATION = "medication"
    LAB = "lab"
    PROCEDURE = "procedure"
    CLINICAL_NOTE = "clinical_note"
    SOAP_NOTE = "soap_note"


class ReferenceType(StrEnum):
    CLINICAL_NOTE = "clinical_note"
    SOAP_NOTE = "soap_note"
    PRESCRIPTION = "prescription"
    LAB_ORDER = "lab_order"
    LAB_RESULT = "lab_result"
    DIFFERENTIAL_DIAGNOSIS = "differential_diagnosis"
    ICD10 = "icd10"
    DOCTOR_REVIEW = "doctor_review"
