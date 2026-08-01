"""Module composition root.

The one place `FamilyAccessQueryPort` gets bound to its concrete
implementation (`FamilyAccessFacade`), and the repository interface gets
bound to its SQLAlchemy implementation. Any future module's
`api/dependencies.py` calls `build_family_access_facade(session)` rather
than constructing `FamilyAccessFacade` (or the repository) directly.

Scope note — this task builds the Family / Caregiver Access module's
**foundation**: the `FamilyAccess` aggregate (an invitation-token-based
access grant from a `Patient` to an existing `User` acting as their
caregiver), its repository, `InviteCaregiver` (which confirms the
patient and the caregiver `User` both exist and belong to the same
organization via the Patient and Authentication modules' public facades,
and enforces "one caregiver cannot have duplicate active access to the
same patient"), `AcceptInvitation`/`RejectInvitation`/`RevokeAccess`
(which together enforce the branching status-transition graph — see
`domain/entities.py`'s own `_ALLOWED_TRANSITIONS`), and the public query
facade (`GetPatientCaregivers`/`GetCaregiverPatients`/`GetInvitation`/
`ListPendingInvitations`, each a `FamilyAccessQueryService` read method
rather than a `UseCase`, per this codebase's own reads-vs-mutations
convention).

This module deliberately does **not** build a frontend, authentication,
RBAC (`app.api.deps.require_permission`/`ensure_same_organization` are
reused as-is, not extended or reimplemented), notifications (no email/SMS
ever gets sent for an invitation — the raw token is returned directly in
`InviteCaregiverOutput`/the API response, and delivering it to the
caregiver is entirely out of scope), or background jobs (per this task's
explicit exclusions), and does not modify the Patient, User, or
Authentication modules or their tables — it only *reads* two of them
(Patient, Authentication) through their public ports.

**Authorization enforcement is explicitly out of scope** — this task's
own business rules state "FullMedical allows all patient record viewing
(authorization integration comes later)" and "ReadOnly cannot modify
data": this module only *records* `access_level`
(`ReadOnly`/`LimitedMedical`/`FullMedical`) and exposes
`FamilyAccessQueryPort.get_active_access_level` for a future
authorization layer to actually gate reads/writes on — no such gating
happens anywhere in this module itself.

Patient Portal, Personal Health Dashboard, Personal Health Timeline, AI
Health Assistant, Emergency Access, Medical Community, Mobile Apps,
Notifications, Audit Log, and a future FHIR `RelatedPerson` mapping are
expected to become their own consumers of `FamilyAccessQueryPort` —
nothing about this module's shape needs to change to support them:
`family_access_id`/`patient_id`/`caregiver_user_id`/`access_level` are
already exactly the fields a `RelatedPerson`/authorization/notification
integration would need to key off of.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.family_access.application.services.family_access_query_service import (
    FamilyAccessQueryService,
)
from app.modules.family_access.infrastructure.repositories import (
    SqlAlchemyFamilyAccessRepository,
)
from app.modules.family_access.public.facade import FamilyAccessFacade


def build_family_access_facade(session: AsyncSession) -> FamilyAccessFacade:
    """Construct a `FamilyAccessFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so it participates in the same transaction
    as the rest of that request's work.
    """
    family_access_repository = SqlAlchemyFamilyAccessRepository(session)

    query_service = FamilyAccessQueryService(family_access_repository=family_access_repository)

    return FamilyAccessFacade(query_service=query_service)
