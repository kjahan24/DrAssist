# SQLAlchemy ORM models are registered here so Alembic autogenerate can
# discover them. Each module owns and physically defines its models under
# its own `infrastructure/models.py`; this file only re-imports them so
# `Base.metadata` (and therefore `alembic revision --autogenerate`) sees
# every table without any module needing to know this file exists — see
# `docs/backend-architecture/01_folder_structure.md` (Evolution note).

from app.modules.authentication.infrastructure import models as authentication_models
from app.modules.doctor.infrastructure import models as doctor_models
from app.modules.organization.infrastructure import models as organization_models

__all__ = ["authentication_models", "doctor_models", "organization_models"]
