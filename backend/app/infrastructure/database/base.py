"""SQLAlchemy declarative base and shared mixins.

All ORM models (`app/infrastructure/database/models/*`) must inherit from
`Base`. A fixed naming convention is set so Alembic generates
deterministic, human-readable constraint names instead of driver defaults.
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Enum as SAEnum

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # Without this, a bare `Mapped[datetime]` annotation resolves to
    # SQLAlchemy's default `DateTime()` — timezone-*naive* — which mismatches
    # every `TIMESTAMPTZ` column this schema actually uses (see
    # `docs/database/00_overview.md`) and raises `asyncpg.DataError` the
    # moment a timezone-aware Python `datetime` is bound to it (confirmed
    # against a real Postgres instance while building the Authentication
    # module: `UserRoleModel.granted_at` failed exactly this way). Mapping
    # `datetime` -> `DateTime(timezone=True)` here, once, means every
    # model's plain `Mapped[datetime]` field is correct with no per-column
    # type argument needed.
    type_annotation_map = {datetime: DateTime(timezone=True)}


def pg_enum(enum_cls: type[Enum], name: str) -> SAEnum:
    """Bind a SQLAlchemy `Enum` column to an already-existing native
    Postgres enum type (`create_type=False` — the Alembic migration owns
    creating the type; the ORM only describes it), using `enum_cls`'s
    string values rather than member names. Shared across every module
    that declares native Postgres enum columns (originally introduced for
    the Doctor module, promoted here once the Patient module needed the
    same helper — see `docs/backend-architecture/01_folder_structure.md`).
    """
    return SAEnum(
        enum_cls,
        name=name,
        create_type=False,
        values_callable=lambda cls: [member.value for member in cls],
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CreatedAtMixin:
    """For append-only, immutable rows that only ever record when they
    were created — no `updated_at` (nothing about the row ever changes),
    no `deleted_at` (it can never be deleted, not even soft-deleted), and
    deliberately not bundled into `TimestampMixin`. First used by the
    Audit Log module's `AuditLogModel` — see
    `docs/database/06_audit_and_activity.md`'s own `reject_mutation()`
    trigger, which enforces this at the database level too.
    """

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class SoftDeleteMixin:
    """`deleted_at IS NULL` means active — see `docs/database/00_overview.md`.

    Tenant-scoped natural-key uniqueness is enforced via partial unique
    indexes `WHERE deleted_at IS NULL` at the migration level, not here.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(default=None)


class AuditActorMixin:
    """Who created/last-updated this row. Always references `users.id`,
    regardless of which table the mixin is applied to — nullable because
    some rows are system/migration-generated with no human actor, and
    `ON DELETE SET NULL` so historical attribution survives even if the
    acting user account is later hard-deleted.
    """

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
