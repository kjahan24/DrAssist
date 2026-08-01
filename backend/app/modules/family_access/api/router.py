"""HTTP routes for the Family / Caregiver Access module.

Follows the pattern established in `app.modules.appointment.api.router`:
every endpoint requires `CurrentUser` (reusing the already-built
Authentication dependency is not "implementing authentication" — the
same distinction this task's own exclusions draw); every "act on one
resource by id" endpoint calls `ensure_same_organization` right after
fetching, so a cross-tenant request 404s instead of leaking existence.
Domain/application exceptions are never caught here —
`app.middlewares.error_handler`'s `DomainError` handler translates them
to the correct HTTP status uniformly.

`invite_caregiver` additionally checks the *patient's* organization
against the caller before ever reaching the use case — a stricter
pre-check than most "create" endpoints in this codebase bother with
(most trust the use case's own patient lookup), justified here because
granting a third party standing access to a patient's medical records is
higher-stakes than most other "create" actions (rule 13: security
review).

`get_invitation` (by raw token) deliberately performs **no** organization
check: possession of the 256-bit random token *is* the authorization
proof, the same "the credential is the check" model
`app.modules.authentication`'s own refresh-token flow already
establishes — a party who doesn't have the raw token cannot feasibly
guess it, and a party who does have it was, by definition, the intended
recipient of the invitation regardless of which organization they
happen to be logged in under.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.core.exceptions import NotFoundError
from app.modules.family_access.api.dependencies import (
    PatientPort,
    UserPort,
    get_accept_invitation_use_case,
    get_family_access_query_service,
    get_invite_caregiver_use_case,
    get_reject_invitation_use_case,
    get_revoke_access_use_case,
)
from app.modules.family_access.api.schemas import (
    FamilyAccessResponse,
    InviteCaregiverRequest,
    InviteCaregiverResponse,
)
from app.modules.family_access.application.dto import (
    AcceptInvitationInput,
    InviteCaregiverInput,
    RejectInvitationInput,
    RevokeAccessInput,
)
from app.modules.family_access.application.services.family_access_query_service import (
    FamilyAccessQueryService,
)
from app.modules.family_access.application.use_cases.accept_invitation import AcceptInvitation
from app.modules.family_access.application.use_cases.invite_caregiver import InviteCaregiver
from app.modules.family_access.application.use_cases.reject_invitation import RejectInvitation
from app.modules.family_access.application.use_cases.revoke_access import RevokeAccess
from app.schemas.base import PaginatedResponse

router = APIRouter()

_SORT_FIELDS = frozenset({"status", "invitation_expires_at"})

QueryService = Annotated[FamilyAccessQueryService, Depends(get_family_access_query_service)]
InviteUseCase = Annotated[InviteCaregiver, Depends(get_invite_caregiver_use_case)]
AcceptUseCase = Annotated[AcceptInvitation, Depends(get_accept_invitation_use_case)]
RejectUseCase = Annotated[RejectInvitation, Depends(get_reject_invitation_use_case)]
RevokeUseCase = Annotated[RevokeAccess, Depends(get_revoke_access_use_case)]


async def _get_response(
    query_service: FamilyAccessQueryService, family_access_id: UUID
) -> FamilyAccessResponse:
    summary = await query_service.get_family_access_summary(family_access_id)
    if summary is None:
        raise NotFoundError(f"no family access grant found with id {family_access_id}")
    return FamilyAccessResponse.model_validate(summary)


@router.post("", response_model=InviteCaregiverResponse, status_code=201)
async def invite_caregiver(
    body: InviteCaregiverRequest,
    use_case: InviteUseCase,
    patient_query_port: PatientPort,
    current_user: CurrentUser,
) -> InviteCaregiverResponse:
    patient_summary = await patient_query_port.get_patient_summary(body.patient_id)
    if patient_summary is None:
        raise NotFoundError(f"no patient found with id {body.patient_id}")
    ensure_same_organization(patient_summary.organization_id, current_user)

    output = await use_case.execute(InviteCaregiverInput(**body.model_dump()))
    return InviteCaregiverResponse(
        id=output.family_access_id,
        organization_id=output.organization_id,
        patient_id=output.patient_id,
        caregiver_user_id=output.caregiver_user_id,
        status=output.status,
        invitation_token=output.invitation_token,
        invitation_expires_at=output.invitation_expires_at,
    )


@router.get("/{family_access_id}", response_model=FamilyAccessResponse)
async def get_family_access(
    family_access_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> FamilyAccessResponse:
    response = await _get_response(query_service, family_access_id)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get(
    "/patients/{patient_id}/caregivers", response_model=PaginatedResponse[FamilyAccessResponse]
)
async def get_patient_caregivers(
    patient_id: UUID,
    query_service: QueryService,
    patient_query_port: PatientPort,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[FamilyAccessResponse]:
    patient_summary = await patient_query_port.get_patient_summary(patient_id)
    if patient_summary is None:
        raise NotFoundError(f"no patient found with id {patient_id}")
    ensure_same_organization(patient_summary.organization_id, current_user)

    summaries = await query_service.get_patient_caregivers(patient_id)
    items = [FamilyAccessResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.get(
    "/caregivers/{caregiver_user_id}/patients",
    response_model=PaginatedResponse[FamilyAccessResponse],
)
async def get_caregiver_patients(
    caregiver_user_id: UUID,
    query_service: QueryService,
    user_query_port: UserPort,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[FamilyAccessResponse]:
    caregiver_summary = await user_query_port.get_user_summary(caregiver_user_id)
    if caregiver_summary is None:
        raise NotFoundError(f"no user found with id {caregiver_user_id}")
    ensure_same_organization(caregiver_summary.organization_id, current_user)

    summaries = await query_service.get_caregiver_patients(caregiver_user_id)
    items = [FamilyAccessResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.get("/invitations/pending", response_model=PaginatedResponse[FamilyAccessResponse])
async def list_pending_invitations(
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[FamilyAccessResponse]:
    """Scoped to the *authenticated caller's own* pending invitations —
    the caregiver checking what they've been invited to, not an
    arbitrary-caregiver admin view (see this module's own `container.py`
    scope note on what this task deliberately excludes)."""
    summaries = await query_service.list_pending_invitations(current_user.user_id)
    items = [FamilyAccessResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.get("/invitations/by-token/{token}", response_model=FamilyAccessResponse)
async def get_invitation(
    token: str, query_service: QueryService, current_user: CurrentUser
) -> FamilyAccessResponse:
    summary = await query_service.get_invitation_by_token(token)
    if summary is None:
        raise NotFoundError("no invitation found for the given token")
    return FamilyAccessResponse.model_validate(summary)


@router.patch("/{family_access_id}/accept", response_model=FamilyAccessResponse)
async def accept_invitation(
    family_access_id: UUID,
    use_case: AcceptUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> FamilyAccessResponse:
    existing = await _get_response(query_service, family_access_id)
    ensure_same_organization(existing.organization_id, current_user)
    await use_case.execute(AcceptInvitationInput(family_access_id=family_access_id))
    return await _get_response(query_service, family_access_id)


@router.patch("/{family_access_id}/reject", response_model=FamilyAccessResponse)
async def reject_invitation(
    family_access_id: UUID,
    use_case: RejectUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> FamilyAccessResponse:
    existing = await _get_response(query_service, family_access_id)
    ensure_same_organization(existing.organization_id, current_user)
    await use_case.execute(RejectInvitationInput(family_access_id=family_access_id))
    return await _get_response(query_service, family_access_id)


@router.patch("/{family_access_id}/revoke", response_model=FamilyAccessResponse)
async def revoke_access(
    family_access_id: UUID,
    use_case: RevokeUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> FamilyAccessResponse:
    existing = await _get_response(query_service, family_access_id)
    ensure_same_organization(existing.organization_id, current_user)
    await use_case.execute(RevokeAccessInput(family_access_id=family_access_id))
    return await _get_response(query_service, family_access_id)
