"""SQLAlchemy ORM model for the Family / Caregiver Access module.

One table: `family_access_grants`. See `app.modules.family_access
.container` for the module's scope note.

`organization_id` uses `RESTRICT` and `patient_id` uses `CASCADE`, the
same choice every other per-patient clinical table in this schema makes
(e.g. `medical_documents`, `appointments`). `caregiver_user_id` is a
required, business-critical relationship FK (not an optional audit-style
attribution column) and uses `RESTRICT`, mirroring `doctors.user_id`'s
own required-reference choice — a user who is actively someone's
caregiver cannot be deleted out from under that grant.

Two business rules are enforced as partial-unique `CheckConstraint`-free
indexes (defense in depth, on top of `FamilyAccess.__post_init__`/its
own methods, the same pattern every prior module's own DB constraints
already establish):
- "Invitation tokens must be unique" ->
  `uq_family_access_grants_invitation_token`, scoped `WHERE deleted_at
  IS NULL` like every other soft-delete-aware uniqueness constraint in
  this schema.
- "One caregiver cannot have duplicate active access to the same
  patient" -> `uq_family_access_grants_active_patient_caregiver`, a
  partial unique index on `(patient_id, caregiver_user_id)` scoped
  `WHERE status IN ('pending', 'accepted') AND deleted_at IS NULL` —
  Postgres partial indexes support arbitrary predicates, so "active"
  (as this module's business rules define it — see
  `domain/repositories.py`'s own docstring) is enforced at the database
  level, not just in the application layer.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.family_access.domain.enums import AccessLevel, FamilyAccessStatus, Relationship

_relationship_enum = pg_enum(Relationship, "family_access_relationship_enum")
_access_level_enum = pg_enum(AccessLevel, "family_access_level_enum")
_family_access_status_enum = pg_enum(FamilyAccessStatus, "family_access_status_enum")


class FamilyAccessModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "family_access_grants"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    caregiver_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    relationship: Mapped[Relationship] = mapped_column(_relationship_enum, nullable=False)
    access_level: Mapped[AccessLevel] = mapped_column(_access_level_enum, nullable=False)
    status: Mapped[FamilyAccessStatus] = mapped_column(_family_access_status_enum, nullable=False)
    invitation_token: Mapped[str] = mapped_column(Text, nullable=False)
    invitation_expires_at: Mapped[datetime] = mapped_column(nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(default=None)
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (
        Index(
            "uq_family_access_grants_invitation_token",
            "invitation_token",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_family_access_grants_active_patient_caregiver",
            "patient_id",
            "caregiver_user_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'accepted') AND deleted_at IS NULL"),
        ),
        Index("ix_family_access_grants_organization_id", "organization_id"),
        Index("ix_family_access_grants_patient_id", "patient_id"),
        Index("ix_family_access_grants_caregiver_user_id", "caregiver_user_id"),
    )
