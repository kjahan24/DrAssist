"""`DefaultMedicalReasoningTemplateSelector` — the one concrete
`MedicalReasoningTemplateSelectorPort` implementation this task ships:
maps a `ReasoningSetting` onto the three registered AI Foundation prompt
template names (`infrastructure/prompts/templates.py`) plus the pinned
version to use.
"""

from app.modules.medical_reasoning_ai.application.ports import (
    MedicalReasoningTemplateSelectorPort,
)
from app.modules.medical_reasoning_ai.domain.enums import ReasoningSetting
from app.modules.medical_reasoning_ai.domain.value_objects import MedicalReasoningTemplateSet
from app.modules.medical_reasoning_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)

_DEFAULT_VERSION = 1


class DefaultMedicalReasoningTemplateSelector(MedicalReasoningTemplateSelectorPort):
    def __init__(self, *, version: int = _DEFAULT_VERSION) -> None:
        self._version = version

    def select(self, reasoning_setting: ReasoningSetting) -> MedicalReasoningTemplateSet:
        return MedicalReasoningTemplateSet(
            system_template_name=system_template_name(reasoning_setting),
            developer_template_name=developer_template_name(reasoning_setting),
            user_template_name=user_template_name(reasoning_setting),
            version=self._version,
        )
