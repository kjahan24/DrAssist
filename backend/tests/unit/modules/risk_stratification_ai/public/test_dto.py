"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.risk_stratification_ai.application.dto import (
    GeneratedRiskStratification as ApplicationGeneratedRiskStratification,
)
from app.modules.risk_stratification_ai.domain.enums import (
    RiskCategory as DomainRiskCategory,
)
from app.modules.risk_stratification_ai.domain.enums import (
    RiskStratificationSetting as DomainRiskStratificationSetting,
)
from app.modules.risk_stratification_ai.domain.value_objects import (
    RiskStratificationInput as DomainRiskStratificationInput,
)
from app.modules.risk_stratification_ai.domain.value_objects import (
    VitalSigns as DomainVitalSigns,
)
from app.modules.risk_stratification_ai.public.dto import (
    GeneratedRiskStratification,
    RiskCategory,
    RiskStratificationInput,
    RiskStratificationSetting,
    VitalSigns,
)


class TestPublicDtoReExports:
    def test_risk_stratification_input_is_the_domain_type(self) -> None:
        assert RiskStratificationInput is DomainRiskStratificationInput

    def test_vital_signs_is_the_domain_type(self) -> None:
        assert VitalSigns is DomainVitalSigns

    def test_generated_risk_stratification_is_the_application_type(self) -> None:
        assert GeneratedRiskStratification is ApplicationGeneratedRiskStratification

    def test_risk_stratification_setting_is_the_domain_type(self) -> None:
        assert RiskStratificationSetting is DomainRiskStratificationSetting

    def test_risk_category_is_the_domain_type(self) -> None:
        assert RiskCategory is DomainRiskCategory
