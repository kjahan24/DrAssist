"""`DefaultPathologyInterpretationTemplateSelector` — the one concrete
`PathologyInterpretationTemplateSelectorPort` implementation this task
ships: maps a `PathologySetting` onto the three registered AI Foundation
prompt template names (`infrastructure/prompts/templates.py`) plus the
pinned version to use.
"""

from app.modules.pathology_interpretation_ai.application.ports import (
    PathologyInterpretationTemplateSelectorPort,
)
from app.modules.pathology_interpretation_ai.domain.enums import PathologySetting
from app.modules.pathology_interpretation_ai.domain.value_objects import (
    PathologyInterpretationTemplateSet,
)
from app.modules.pathology_interpretation_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)

_DEFAULT_VERSION = 1


class DefaultPathologyInterpretationTemplateSelector(PathologyInterpretationTemplateSelectorPort):
    def __init__(self, *, version: int = _DEFAULT_VERSION) -> None:
        self._version = version

    def select(self, pathology_setting: PathologySetting) -> PathologyInterpretationTemplateSet:
        return PathologyInterpretationTemplateSet(
            system_template_name=system_template_name(pathology_setting),
            developer_template_name=developer_template_name(pathology_setting),
            user_template_name=user_template_name(pathology_setting),
            version=self._version,
        )
