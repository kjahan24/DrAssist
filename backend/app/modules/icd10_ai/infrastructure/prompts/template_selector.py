"""`DefaultICD10TemplateSelector` — the one concrete
`ICD10TemplateSelectorPort` implementation this task ships: maps a
`CodingSetting` onto the three registered AI Foundation prompt template
names (`infrastructure/prompts/templates.py`) plus the pinned version to
use.
"""

from app.modules.icd10_ai.application.ports import ICD10TemplateSelectorPort
from app.modules.icd10_ai.domain.enums import CodingSetting
from app.modules.icd10_ai.domain.value_objects import ICD10TemplateSet
from app.modules.icd10_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)

_DEFAULT_VERSION = 1


class DefaultICD10TemplateSelector(ICD10TemplateSelectorPort):
    def __init__(self, *, version: int = _DEFAULT_VERSION) -> None:
        self._version = version

    def select(self, coding_setting: CodingSetting) -> ICD10TemplateSet:
        return ICD10TemplateSet(
            system_template_name=system_template_name(coding_setting),
            developer_template_name=developer_template_name(coding_setting),
            user_template_name=user_template_name(coding_setting),
            version=self._version,
        )
