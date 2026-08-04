"""`DefaultSOAPTemplateSelector` — the one concrete
`SOAPTemplateSelectorPort` implementation this task ships: maps a
`SOAPStyle` onto the three registered AI Foundation prompt template names
(`infrastructure/prompts/templates.py`) plus the pinned version to use.
"""

from app.modules.soap_note_ai.application.ports import SOAPTemplateSelectorPort
from app.modules.soap_note_ai.domain.enums import SOAPStyle
from app.modules.soap_note_ai.domain.value_objects import SOAPTemplateSet
from app.modules.soap_note_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)

_DEFAULT_VERSION = 1


class DefaultSOAPTemplateSelector(SOAPTemplateSelectorPort):
    def __init__(self, *, version: int = _DEFAULT_VERSION) -> None:
        self._version = version

    def select(self, soap_style: SOAPStyle) -> SOAPTemplateSet:
        return SOAPTemplateSet(
            system_template_name=system_template_name(soap_style),
            developer_template_name=developer_template_name(soap_style),
            user_template_name=user_template_name(soap_style),
            version=self._version,
        )
