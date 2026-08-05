"""`StaticPatientEducationKnowledgeBase` — the one concrete
`PatientEducationPort` implementation this task ships: a curated,
necessarily-incomplete reference table of patient-friendly diagnosis
explanations and their standard warning signs/emergency symptoms, the
same "each module defines its own local, necessarily-incomplete copy"
precedent every prior AI module's own knowledge-base adapter
establishes for itself. A real production system might instead consult
a licensed, comprehensive patient-education content library; this is
the pragmatic in-repo substitute.

Matched against a diagnosis string by case-insensitive keyword
containment (the same matching style
`app.modules.risk_stratification_ai.infrastructure.clinical_risk
.static_clinical_risk_knowledge_base.StaticClinicalRiskKnowledgeBase`
uses for its own diagnosis-keyed table). Returns `None`/an empty tuple
when no curated keyword matches, rather than fabricating educational
content for a diagnosis this port does not actually have reference data
for.
"""

from dataclasses import dataclass

from app.modules.patient_education_ai.application.ports import PatientEducationPort


@dataclass(frozen=True)
class _DiagnosisEducation:
    explanation: str
    warning_signs: tuple[str, ...]
    emergency_symptoms: tuple[str, ...]


_DIAGNOSIS_EDUCATION: dict[str, _DiagnosisEducation] = {
    "hypertension": _DiagnosisEducation(
        explanation=(
            "Hypertension means your blood pressure is higher than it should be, which "
            "makes your heart and blood vessels work harder over time."
        ),
        warning_signs=("Severe headache", "Blurred vision", "Chest pain"),
        emergency_symptoms=("Blood pressure reading above 180/120", "Difficulty speaking"),
    ),
    "diabetes": _DiagnosisEducation(
        explanation=(
            "Diabetes means your body has trouble keeping your blood sugar in a healthy "
            "range, which can affect your heart, eyes, nerves, and kidneys over time."
        ),
        warning_signs=("Excessive thirst", "Frequent urination", "Blurred vision"),
        emergency_symptoms=("Confusion or difficulty waking", "Fruity-smelling breath"),
    ),
    "asthma": _DiagnosisEducation(
        explanation=(
            "Asthma means your airways can become narrow and inflamed, making it harder "
            "to breathe, especially around certain triggers."
        ),
        warning_signs=("Increased use of rescue inhaler", "Wheezing", "Chest tightness"),
        emergency_symptoms=("Severe shortness of breath", "Bluish lips or fingertips"),
    ),
    "copd": _DiagnosisEducation(
        explanation=(
            "COPD means your airways and lungs are damaged in a way that makes breathing "
            "progressively harder, especially with exertion."
        ),
        warning_signs=("Increased shortness of breath", "More coughing than usual"),
        emergency_symptoms=("Severe difficulty breathing at rest", "Bluish lips or fingertips"),
    ),
    "heart failure": _DiagnosisEducation(
        explanation=(
            "Heart failure means your heart isn't pumping blood as well as it should, "
            "which can cause fluid to build up in your lungs and body."
        ),
        warning_signs=("Sudden weight gain", "Increased swelling in legs", "Shortness of breath"),
        emergency_symptoms=("Severe shortness of breath at rest", "Chest pain"),
    ),
    "pneumonia": _DiagnosisEducation(
        explanation=(
            "Pneumonia is an infection in your lungs that can cause cough, fever, and "
            "difficulty breathing."
        ),
        warning_signs=("Fever that does not improve", "Worsening cough"),
        emergency_symptoms=("Severe difficulty breathing", "Confusion"),
    ),
    "urinary tract infection": _DiagnosisEducation(
        explanation=(
            "A urinary tract infection is an infection in your bladder or urinary system "
            "that can cause pain or burning when you urinate."
        ),
        warning_signs=("Fever", "Back or side pain", "Blood in urine"),
        emergency_symptoms=("High fever with chills", "Severe back pain"),
    ),
    "coronary artery disease": _DiagnosisEducation(
        explanation=(
            "Coronary artery disease means the blood vessels supplying your heart are "
            "narrowed, which can limit blood flow to your heart muscle."
        ),
        warning_signs=("Chest discomfort with activity", "Shortness of breath"),
        emergency_symptoms=("Chest pain at rest", "Pain spreading to arm or jaw"),
    ),
    "chronic kidney disease": _DiagnosisEducation(
        explanation=(
            "Chronic kidney disease means your kidneys are not filtering waste from your "
            "blood as well as they should."
        ),
        warning_signs=("Swelling in legs or ankles", "Fatigue", "Changes in urination"),
        emergency_symptoms=("Little or no urination", "Severe shortness of breath"),
    ),
    "stroke": _DiagnosisEducation(
        explanation=(
            "A stroke happens when blood flow to part of your brain is interrupted, which "
            "can affect movement, speech, and other functions."
        ),
        warning_signs=("New weakness or numbness", "Difficulty speaking", "Vision changes"),
        emergency_symptoms=("Sudden facial drooping", "Sudden severe headache"),
    ),
}


def _match(diagnosis: str) -> _DiagnosisEducation | None:
    normalized = diagnosis.strip().lower()
    for keyword, education in _DIAGNOSIS_EDUCATION.items():
        if keyword in normalized:
            return education
    return None


class StaticPatientEducationKnowledgeBase(PatientEducationPort):
    def explain_diagnosis(self, diagnosis: str) -> str | None:
        education = _match(diagnosis)
        return education.explanation if education is not None else None

    def identify_warning_signs(self, diagnosis: str) -> tuple[str, ...]:
        education = _match(diagnosis)
        return education.warning_signs if education is not None else ()

    def identify_emergency_symptoms(self, diagnosis: str) -> tuple[str, ...]:
        education = _match(diagnosis)
        return education.emergency_symptoms if education is not None else ()
