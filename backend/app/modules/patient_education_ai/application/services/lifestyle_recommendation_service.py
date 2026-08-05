"""`LifestyleRecommendationService` — this task's own explicitly-named
APPLICATION service, the thin orchestration layer over
`LifestyleRecommendationPort`:

- `collect_lifestyle_advice`/`collect_diet_advice`/`collect_exercise_advice`
  — this task's own "Lifestyle Advice"/"Diet Advice"/"Exercise Advice"
  OUTPUT fields.
- `collect_preventive_care_recommendations` — covers this task's own
  "Preventive recommendations" and "Vaccination reminders" GENERATE
  items, neither of which this task's own OUTPUT section names a
  dedicated field for. `application/use_cases
  /generate_patient_education.py` merges this collection into the
  "Follow-up Plan" OUTPUT field — a preventive-care or vaccination
  reminder is, in substance, something the patient still needs to
  follow up on, the same reasoning used to fold "Wound care
  instructions" into "Home Care Plan" in `DischargeInstructionService`'s
  own docstring.
"""

from app.modules.patient_education_ai.application.ports import LifestyleRecommendationPort


class LifestyleRecommendationService:
    def __init__(self, *, lifestyle_recommendation_port: LifestyleRecommendationPort) -> None:
        self._lifestyle_recommendation_port = lifestyle_recommendation_port

    def collect_lifestyle_advice(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]:
        return self._lifestyle_recommendation_port.recommend_lifestyle(diagnoses)

    def collect_diet_advice(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]:
        return self._lifestyle_recommendation_port.recommend_diet(diagnoses)

    def collect_exercise_advice(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]:
        return self._lifestyle_recommendation_port.recommend_exercise(diagnoses)

    def collect_preventive_care_recommendations(
        self, diagnoses: tuple[str, ...], patient_age: int | None
    ) -> tuple[str, ...]:
        return self._lifestyle_recommendation_port.recommend_preventive_care(diagnoses, patient_age)
