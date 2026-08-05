"""`StaticLifestyleRecommendationKnowledgeBase` — the one concrete
`LifestyleRecommendationPort` implementation this task ships: a
curated, necessarily-incomplete reference table of lifestyle, diet,
exercise, and preventive-care/vaccination recommendations keyed by
diagnosis keyword (and, for preventive care, patient age), the same
"each module defines its own local, necessarily-incomplete copy"
precedent every prior AI module's own knowledge-base adapter
establishes for itself.

`recommend_preventive_care` combines age-based reminders (independent
of diagnosis — anyone above the given age threshold gets the reminder)
with diagnosis-specific preventive care, covering both "Preventive
recommendations" and "Vaccination reminders" from this task's own
GENERATE section.
"""

from app.modules.patient_education_ai.application.ports import LifestyleRecommendationPort

_FLU_VACCINE_MIN_AGE = 6
_PNEUMONIA_VACCINE_MIN_AGE = 65
_COLORECTAL_SCREENING_MIN_AGE = 45

_LIFESTYLE_BY_DIAGNOSIS: dict[str, tuple[str, ...]] = {
    "hypertension": ("Limit alcohol intake and manage stress.",),
    "diabetes": ("Monitor your blood sugar regularly and maintain a healthy weight.",),
    "asthma": ("Avoid known triggers such as smoke, dust, and strong odors.",),
    "copd": ("Avoid smoking and secondhand smoke exposure.",),
    "heart failure": ("Limit sodium intake and monitor your weight daily.",),
    "coronary artery disease": ("Avoid smoking and manage stress.",),
    "chronic kidney disease": (
        "Avoid over-the-counter pain relievers unless approved by your doctor.",
    ),
    "obesity": ("Aim for gradual, sustainable weight loss with your care team's guidance.",),
}

_DIET_BY_DIAGNOSIS: dict[str, tuple[str, ...]] = {
    "hypertension": ("Follow a low-sodium diet.",),
    "diabetes": ("Follow a balanced diet with controlled carbohydrate portions.",),
    "heart failure": ("Follow a low-sodium, fluid-conscious diet as directed.",),
    "coronary artery disease": ("Follow a heart-healthy diet low in saturated fat.",),
    "chronic kidney disease": (
        "Follow any potassium, phosphorus, or protein restrictions your doctor gave you.",
    ),
    "obesity": ("Focus on portion control and nutrient-dense foods.",),
}

_EXERCISE_BY_DIAGNOSIS: dict[str, tuple[str, ...]] = {
    "hypertension": ("Aim for regular moderate aerobic activity as approved by your doctor.",),
    "diabetes": ("Aim for regular physical activity to help manage blood sugar.",),
    "asthma": ("Warm up before exercise and keep your rescue inhaler nearby.",),
    "copd": ("Ask about a pulmonary rehabilitation program.",),
    "heart failure": ("Follow your care team's guidance on safe activity levels.",),
    "coronary artery disease": ("Ask about a cardiac rehabilitation program.",),
    "obesity": ("Build up physical activity gradually with your care team's guidance.",),
    "stroke": ("Follow your prescribed physical therapy exercise plan.",),
}

_PREVENTIVE_BY_DIAGNOSIS: dict[str, tuple[str, ...]] = {
    "diabetes": ("Schedule an annual eye exam and foot check.",),
    "hypertension": ("Have your blood pressure checked regularly.",),
    "coronary artery disease": ("Have your cholesterol checked regularly.",),
    "chronic kidney disease": ("Have your kidney function checked regularly.",),
}


def _collect_by_diagnosis(
    diagnoses: tuple[str, ...], table: dict[str, tuple[str, ...]]
) -> tuple[str, ...]:
    items: list[str] = []
    for diagnosis in diagnoses:
        normalized = diagnosis.strip().lower()
        for keyword, values in table.items():
            if keyword in normalized:
                items.extend(values)
    return tuple(dict.fromkeys(items))


class StaticLifestyleRecommendationKnowledgeBase(LifestyleRecommendationPort):
    def recommend_lifestyle(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]:
        return _collect_by_diagnosis(diagnoses, _LIFESTYLE_BY_DIAGNOSIS)

    def recommend_diet(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]:
        return _collect_by_diagnosis(diagnoses, _DIET_BY_DIAGNOSIS)

    def recommend_exercise(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]:
        return _collect_by_diagnosis(diagnoses, _EXERCISE_BY_DIAGNOSIS)

    def recommend_preventive_care(
        self, diagnoses: tuple[str, ...], patient_age: int | None
    ) -> tuple[str, ...]:
        reminders: list[str] = list(_collect_by_diagnosis(diagnoses, _PREVENTIVE_BY_DIAGNOSIS))
        if patient_age is not None:
            if patient_age >= _FLU_VACCINE_MIN_AGE:
                reminders.append("Stay up to date on your annual flu vaccine.")
            if patient_age >= _PNEUMONIA_VACCINE_MIN_AGE:
                reminders.append("Ask your doctor about the pneumonia vaccine.")
            if patient_age >= _COLORECTAL_SCREENING_MIN_AGE:
                reminders.append("Ask your doctor about colorectal cancer screening.")
        return tuple(dict.fromkeys(reminders))
