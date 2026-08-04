"""`DefaultPrescriptionTemplateSelector` — the one concrete
`PrescriptionTemplateSelectorPort` implementation this task ships: maps a
`PrescribingSetting` onto the three registered AI Foundation prompt
template names (`infrastructure/prompts/templates.py`) plus the pinned
version to use.
"""

from app.modules.prescription_ai.application.ports import PrescriptionTemplateSelectorPort
from app.modules.prescription_ai.domain.enums import PrescribingSetting
from app.modules.prescription_ai.domain.value_objects import PrescriptionTemplateSet
from app.modules.prescription_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)

_DEFAULT_VERSION = 1


class DefaultPrescriptionTemplateSelector(PrescriptionTemplateSelectorPort):
    def __init__(self, *, version: int = _DEFAULT_VERSION) -> None:
        self._version = version

    def select(self, prescribing_setting: PrescribingSetting) -> PrescriptionTemplateSet:
        return PrescriptionTemplateSet(
            system_template_name=system_template_name(prescribing_setting),
            developer_template_name=developer_template_name(prescribing_setting),
            user_template_name=user_template_name(prescribing_setting),
            version=self._version,
        )
