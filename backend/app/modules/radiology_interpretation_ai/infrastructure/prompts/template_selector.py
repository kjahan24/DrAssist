"""`DefaultRadiologyInterpretationTemplateSelector` — the one concrete
`RadiologyInterpretationTemplateSelectorPort` implementation this task
ships: maps a `RadiologySetting` onto the three registered AI Foundation
prompt template names (`infrastructure/prompts/templates.py`) plus the
pinned version to use.
"""

from app.modules.radiology_interpretation_ai.application.ports import (
    RadiologyInterpretationTemplateSelectorPort,
)
from app.modules.radiology_interpretation_ai.domain.enums import RadiologySetting
from app.modules.radiology_interpretation_ai.domain.value_objects import (
    RadiologyInterpretationTemplateSet,
)
from app.modules.radiology_interpretation_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)

_DEFAULT_VERSION = 1


class DefaultRadiologyInterpretationTemplateSelector(RadiologyInterpretationTemplateSelectorPort):
    def __init__(self, *, version: int = _DEFAULT_VERSION) -> None:
        self._version = version

    def select(self, radiology_setting: RadiologySetting) -> RadiologyInterpretationTemplateSet:
        return RadiologyInterpretationTemplateSet(
            system_template_name=system_template_name(radiology_setting),
            developer_template_name=developer_template_name(radiology_setting),
            user_template_name=user_template_name(radiology_setting),
            version=self._version,
        )
