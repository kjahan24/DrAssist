"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.drug_interaction_ai.application.dto import (
    GeneratedDrugInteractionAnalysis as ApplicationGeneratedDrugInteractionAnalysis,
)
from app.modules.drug_interaction_ai.domain.enums import (
    DrugInteractionSetting as DomainDrugInteractionSetting,
)
from app.modules.drug_interaction_ai.domain.enums import (
    SafetyIssueCategory as DomainSafetyIssueCategory,
)
from app.modules.drug_interaction_ai.domain.value_objects import (
    DrugInteractionAnalysisInput as DomainDrugInteractionAnalysisInput,
)
from app.modules.drug_interaction_ai.domain.value_objects import (
    MedicationEntry as DomainMedicationEntry,
)
from app.modules.drug_interaction_ai.public.dto import (
    DrugInteractionAnalysisInput,
    DrugInteractionSetting,
    GeneratedDrugInteractionAnalysis,
    MedicationEntry,
    SafetyIssueCategory,
)


class TestPublicDtoReExports:
    def test_drug_interaction_analysis_input_is_the_domain_type(self) -> None:
        assert DrugInteractionAnalysisInput is DomainDrugInteractionAnalysisInput

    def test_medication_entry_is_the_domain_type(self) -> None:
        assert MedicationEntry is DomainMedicationEntry

    def test_generated_drug_interaction_analysis_is_the_application_type(self) -> None:
        assert GeneratedDrugInteractionAnalysis is ApplicationGeneratedDrugInteractionAnalysis

    def test_drug_interaction_setting_is_the_domain_type(self) -> None:
        assert DrugInteractionSetting is DomainDrugInteractionSetting

    def test_safety_issue_category_is_the_domain_type(self) -> None:
        assert SafetyIssueCategory is DomainSafetyIssueCategory
