"""Enums owned by the Personal Health Timeline module's domain.

`TimelineSourceModule` names *which* existing module a `TimelineEvent`
was aggregated from. `TimelineEventType` is the fine-grained kind of
event within that source. `TimelineEventCategory` is a coarser grouping
across sources, used for icon/color theming and future category-level
filtering — e.g. `CLINICAL_DOCUMENTATION` covers both `CLINICAL_NOTE` and
`SOAP_NOTE` events.

`VACCINATION`/`WEARABLE_DEVICE_READING`/`AI_INSIGHT` (and their matching
`TimelineSourceModule`/`TimelineEventCategory` members) are reserved,
future-ready placeholders per this task's own "Future-ready placeholders
only (no implementation)" instruction — `TimelineAggregationService`
never produces an event with one of these types today; they exist only
so a future Vaccinations/Wearable Devices/AI Insights module can be
plugged into this same enum without a breaking change to any consumer
that already switches on `TimelineEventType`.
"""

from enum import StrEnum


class TimelineSourceModule(StrEnum):
    APPOINTMENT = "appointment"
    VISIT = "visit"
    CLINICAL_NOTES = "clinical_notes"
    SOAP_NOTES = "soap_notes"
    PRESCRIPTIONS = "prescriptions"
    LAB_ORDERS = "lab_orders"
    LAB_RESULTS = "lab_results"
    DOCUMENTS = "documents"
    PATIENT = "patient"  # Allergies / Medical Conditions (patient sub-resources)
    DOCTOR_REVIEW = "doctor_review"
    # Reserved — no implementation yet.
    VACCINATIONS = "vaccinations"
    WEARABLE_DEVICES = "wearable_devices"
    AI_INSIGHTS = "ai_insights"


class TimelineEventType(StrEnum):
    APPOINTMENT = "appointment"
    VISIT = "visit"
    CLINICAL_NOTE = "clinical_note"
    SOAP_NOTE = "soap_note"
    PRESCRIPTION = "prescription"
    LAB_ORDER = "lab_order"
    LAB_RESULT = "lab_result"
    DOCUMENT = "document"
    ALLERGY = "allergy"
    MEDICAL_CONDITION = "medical_condition"
    DOCTOR_REVIEW = "doctor_review"
    # Reserved — no implementation yet.
    VACCINATION = "vaccination"
    WEARABLE_DEVICE_READING = "wearable_device_reading"
    AI_INSIGHT = "ai_insight"


class TimelineEventCategory(StrEnum):
    SCHEDULING = "scheduling"
    CLINICAL_DOCUMENTATION = "clinical_documentation"
    MEDICATION = "medication"
    DIAGNOSTICS = "diagnostics"
    DOCUMENT = "document"
    HEALTH_RECORD = "health_record"
    REVIEW = "review"
    # Reserved — no implementation yet.
    WEARABLE = "wearable"
    AI = "ai"
