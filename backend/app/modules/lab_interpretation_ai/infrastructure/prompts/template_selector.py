"""`DefaultLabInterpretationTemplateSelector` — the one concrete
`LabInterpretationTemplateSelectorPort` implementation this task ships:
maps a `LabInterpretationSetting` onto the three registered AI Foundation
prompt template names (`infrastructure/prompts/templates.py`) plus the
pinned version to use.
"""

from app.modules.lab_interpretation_ai.application.ports import (
    LabInterpretationTemplateSelectorPort,
)
from app.modules.lab_interpretation_ai.domain.enums import LabInterpretationSetting
from app.modules.lab_interpretation_ai.domain.value_objects import LabInterpretationTemplateSet
from app.modules.lab_interpretation_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)

_DEFAULT_VERSION = 1


class DefaultLabInterpretationTemplateSelector(LabInterpretationTemplateSelectorPort):
    def __init__(self, *, version: int = _DEFAULT_VERSION) -> None:
        self._version = version

    def select(self, lab_setting: LabInterpretationSetting) -> LabInterpretationTemplateSet:
        return LabInterpretationTemplateSet(
            system_template_name=system_template_name(lab_setting),
            developer_template_name=developer_template_name(lab_setting),
            user_template_name=user_template_name(lab_setting),
            version=self._version,
        )
