# SQLAlchemy ORM models are registered here so Alembic autogenerate can
# discover them. Each module owns and physically defines its models under
# its own `infrastructure/models.py`; this file only re-imports them so
# `Base.metadata` (and therefore `alembic revision --autogenerate`) sees
# every table without any module needing to know this file exists — see
# `docs/backend-architecture/01_folder_structure.md` (Evolution note).

from app.modules.appointment.infrastructure import models as appointment_models
from app.modules.attachments.infrastructure import models as attachments_models
from app.modules.authentication.infrastructure import models as authentication_models
from app.modules.chief_complaints.infrastructure import models as chief_complaints_models
from app.modules.clinical_notes.infrastructure import models as clinical_notes_models
from app.modules.clinical_reasoning.infrastructure import models as clinical_reasoning_models
from app.modules.diagnosis.infrastructure import models as diagnosis_models
from app.modules.differential_diagnosis.infrastructure import (
    models as differential_diagnosis_models,
)
from app.modules.doctor.infrastructure import models as doctor_models
from app.modules.doctor_review.infrastructure import models as doctor_review_models
from app.modules.icd10_coding.infrastructure import models as icd10_coding_models
from app.modules.lab_orders.infrastructure import models as lab_orders_models
from app.modules.lab_results.infrastructure import models as lab_results_models
from app.modules.organization.infrastructure import models as organization_models
from app.modules.patient.infrastructure import models as patient_models
from app.modules.patient_history.infrastructure import models as patient_history_models
from app.modules.prescriptions.infrastructure import models as prescriptions_models
from app.modules.procedures.infrastructure import models as procedures_models
from app.modules.soap_notes.infrastructure import models as soap_notes_models
from app.modules.visit.infrastructure import models as visit_models
from app.modules.vital_signs.infrastructure import models as vital_signs_models

__all__ = [
    "appointment_models",
    "attachments_models",
    "authentication_models",
    "chief_complaints_models",
    "clinical_notes_models",
    "clinical_reasoning_models",
    "diagnosis_models",
    "differential_diagnosis_models",
    "doctor_models",
    "doctor_review_models",
    "icd10_coding_models",
    "lab_orders_models",
    "lab_results_models",
    "organization_models",
    "patient_history_models",
    "patient_models",
    "prescriptions_models",
    "procedures_models",
    "soap_notes_models",
    "visit_models",
    "vital_signs_models",
]
