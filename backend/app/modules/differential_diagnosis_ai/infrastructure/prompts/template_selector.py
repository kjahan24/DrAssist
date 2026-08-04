"""`DefaultDifferentialDiagnosisTemplateSelector` — the one concrete
`DifferentialDiagnosisTemplateSelectorPort` implementation this task
ships: maps a `ClinicalSetting` onto the three registered AI Foundation
prompt template names (`infrastructure/prompts/templates.py`) plus the
pinned version to use.
"""

from app.modules.differential_diagnosis_ai.application.ports import (
    DifferentialDiagnosisTemplateSelectorPort,
)
from app.modules.differential_diagnosis_ai.domain.enums import ClinicalSetting
from app.modules.differential_diagnosis_ai.domain.value_objects import (
    DifferentialDiagnosisTemplateSet,
)
from app.modules.differential_diagnosis_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)

_DEFAULT_VERSION = 1


class DefaultDifferentialDiagnosisTemplateSelector(DifferentialDiagnosisTemplateSelectorPort):
    def __init__(self, *, version: int = _DEFAULT_VERSION) -> None:
        self._version = version

    def select(self, clinical_setting: ClinicalSetting) -> DifferentialDiagnosisTemplateSet:
        return DifferentialDiagnosisTemplateSet(
            system_template_name=system_template_name(clinical_setting),
            developer_template_name=developer_template_name(clinical_setting),
            user_template_name=user_template_name(clinical_setting),
            version=self._version,
        )
