"""`DefaultPatientEducationAnalysisTemplateSelector` — the one concrete
`PatientEducationAnalysisTemplateSelectorPort` implementation this task
ships: maps a `PatientEducationSetting` onto the three registered AI
Foundation prompt template names (`infrastructure/prompts/templates.py`)
plus the pinned version to use.
"""

from app.modules.patient_education_ai.application.ports import (
    PatientEducationAnalysisTemplateSelectorPort,
)
from app.modules.patient_education_ai.domain.enums import PatientEducationSetting
from app.modules.patient_education_ai.domain.value_objects import PatientEducationTemplateSet
from app.modules.patient_education_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)

_DEFAULT_VERSION = 1


class DefaultPatientEducationAnalysisTemplateSelector(PatientEducationAnalysisTemplateSelectorPort):
    def __init__(self, *, version: int = _DEFAULT_VERSION) -> None:
        self._version = version

    def select(self, education_setting: PatientEducationSetting) -> PatientEducationTemplateSet:
        return PatientEducationTemplateSet(
            system_template_name=system_template_name(education_setting),
            developer_template_name=developer_template_name(education_setting),
            user_template_name=user_template_name(education_setting),
            version=self._version,
        )
