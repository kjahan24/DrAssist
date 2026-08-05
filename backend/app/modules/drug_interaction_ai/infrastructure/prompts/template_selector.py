"""`DefaultDrugSafetyAnalysisTemplateSelector` — the one concrete
`DrugSafetyAnalysisTemplateSelectorPort` implementation this task ships:
maps a `DrugInteractionSetting` onto the three registered AI Foundation
prompt template names (`infrastructure/prompts/templates.py`) plus the
pinned version to use.
"""

from app.modules.drug_interaction_ai.application.ports import (
    DrugSafetyAnalysisTemplateSelectorPort,
)
from app.modules.drug_interaction_ai.domain.enums import DrugInteractionSetting
from app.modules.drug_interaction_ai.domain.value_objects import DrugInteractionTemplateSet
from app.modules.drug_interaction_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)

_DEFAULT_VERSION = 1


class DefaultDrugSafetyAnalysisTemplateSelector(DrugSafetyAnalysisTemplateSelectorPort):
    def __init__(self, *, version: int = _DEFAULT_VERSION) -> None:
        self._version = version

    def select(self, medication_setting: DrugInteractionSetting) -> DrugInteractionTemplateSet:
        return DrugInteractionTemplateSet(
            system_template_name=system_template_name(medication_setting),
            developer_template_name=developer_template_name(medication_setting),
            user_template_name=user_template_name(medication_setting),
            version=self._version,
        )
