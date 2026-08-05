"""`DefaultRiskStratificationAnalysisTemplateSelector` — the one
concrete `RiskStratificationAnalysisTemplateSelectorPort` implementation
this task ships: maps a `RiskStratificationSetting` onto the three
registered AI Foundation prompt template names
(`infrastructure/prompts/templates.py`) plus the pinned version to use.
"""

from app.modules.risk_stratification_ai.application.ports import (
    RiskStratificationAnalysisTemplateSelectorPort,
)
from app.modules.risk_stratification_ai.domain.enums import RiskStratificationSetting
from app.modules.risk_stratification_ai.domain.value_objects import (
    RiskStratificationTemplateSet,
)
from app.modules.risk_stratification_ai.infrastructure.prompts.templates import (
    developer_template_name,
    system_template_name,
    user_template_name,
)

_DEFAULT_VERSION = 1


class DefaultRiskStratificationAnalysisTemplateSelector(
    RiskStratificationAnalysisTemplateSelectorPort
):
    def __init__(self, *, version: int = _DEFAULT_VERSION) -> None:
        self._version = version

    def select(self, risk_setting: RiskStratificationSetting) -> RiskStratificationTemplateSet:
        return RiskStratificationTemplateSet(
            system_template_name=system_template_name(risk_setting),
            developer_template_name=developer_template_name(risk_setting),
            user_template_name=user_template_name(risk_setting),
            version=self._version,
        )
