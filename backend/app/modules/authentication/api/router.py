"""HTTP routes for the Authentication module.

Covers the RBAC administration surface (`Role`/`Permission`/assignments),
a read-only `GET /users/{user_id}`, and — added for the current
frontend's Sign Up / Sign In pages — `POST /register` and `POST /login`
(see `application/use_cases/register_user.py`/`.authenticate_user.py` for
the full design). Refresh/logout remain out of scope: no frontend page
calls either today, and building them without a real caller would be
exactly the kind of speculative surface this codebase avoids elsewhere.

Neither `register` nor `login` depends on `CurrentUser` — by definition,
no authenticated principal exists yet for either request, the same
reasoning `app.modules.organization.api.router`'s own `POST /organizations`
docstring gives for itself.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.core.exceptions import NotFoundError
from app.modules.authentication.api.dependencies import (
    get_activate_role_use_case,
    get_assign_permission_to_role_use_case,
    get_assign_role_to_user_use_case,
    get_authenticate_user_use_case,
    get_create_permission_use_case,
    get_create_role_use_case,
    get_deactivate_role_use_case,
    get_delete_role_use_case,
    get_permission_query_service,
    get_register_user_use_case,
    get_role_query_service,
    get_user_query_port,
)
from app.modules.authentication.api.schemas import (
    AssignPermissionToRoleRequest,
    AssignRoleToUserRequest,
    CreatePermissionRequest,
    CreateRoleRequest,
    LoginRequest,
    LoginResponse,
    PermissionResponse,
    RegisterRequest,
    RegisterResponse,
    RoleResponse,
    UserResponse,
)
from app.modules.authentication.application.dto import (
    ActivateRoleInput,
    AssignPermissionToRoleInput,
    AssignRoleToUserInput,
    AuthenticateUserInput,
    CreatePermissionInput,
    CreateRoleInput,
    DeactivateRoleInput,
    DeleteRoleInput,
    RegisterUserInput,
)
from app.modules.authentication.application.services.permission_query_service import (
    PermissionQueryService,
)
from app.modules.authentication.application.services.role_query_service import RoleQueryService
from app.modules.authentication.application.use_cases.activate_role import ActivateRole
from app.modules.authentication.application.use_cases.assign_permission_to_role import (
    AssignPermissionToRole,
)
from app.modules.authentication.application.use_cases.assign_role_to_user import (
    AssignRoleToUser,
)
from app.modules.authentication.application.use_cases.authenticate_user import AuthenticateUser
from app.modules.authentication.application.use_cases.create_permission import CreatePermission
from app.modules.authentication.application.use_cases.create_role import CreateRole
from app.modules.authentication.application.use_cases.deactivate_role import DeactivateRole
from app.modules.authentication.application.use_cases.delete_role import DeleteRole
from app.modules.authentication.application.use_cases.register_user import RegisterUser
from app.modules.authentication.public.interfaces import UserQueryPort
from app.schemas.base import PaginatedResponse

router = APIRouter()

UserPort = Annotated[UserQueryPort, Depends(get_user_query_port)]
RoleQS = Annotated[RoleQueryService, Depends(get_role_query_service)]
PermissionQS = Annotated[PermissionQueryService, Depends(get_permission_query_service)]

CreateRoleUseCase = Annotated[CreateRole, Depends(get_create_role_use_case)]
DeleteRoleUseCase = Annotated[DeleteRole, Depends(get_delete_role_use_case)]
ActivateRoleUseCase = Annotated[ActivateRole, Depends(get_activate_role_use_case)]
DeactivateRoleUseCase = Annotated[DeactivateRole, Depends(get_deactivate_role_use_case)]
CreatePermissionUseCase = Annotated[CreatePermission, Depends(get_create_permission_use_case)]
AssignPermissionUseCase = Annotated[
    AssignPermissionToRole, Depends(get_assign_permission_to_role_use_case)
]
AssignRoleUseCase = Annotated[AssignRoleToUser, Depends(get_assign_role_to_user_use_case)]
RegisterUseCase = Annotated[RegisterUser, Depends(get_register_user_use_case)]
LoginUseCase = Annotated[AuthenticateUser, Depends(get_authenticate_user_use_case)]


def _ensure_same_organization_if_scoped(
    organization_id: UUID | None, current_user: CurrentUser
) -> None:
    """`Role.organization_id` is `None` for system roles, which every
    organization can read — only an organization-scoped role needs the
    tenant-isolation check."""
    if organization_id is not None:
        ensure_same_organization(organization_id, current_user)


async def _get_role_response(
    role_id: UUID, query_service: RoleQS, current_user: CurrentUser
) -> RoleResponse:
    summary = await query_service.get_role_summary(role_id)
    if summary is None:
        raise NotFoundError(f"no role found with id {role_id}")
    response = RoleResponse.model_validate(summary)
    _ensure_same_organization_if_scoped(response.organization_id, current_user)
    return response


async def _get_permission_response(
    permission_id: UUID, query_service: PermissionQS
) -> PermissionResponse:
    summary = await query_service.get_permission_summary(permission_id)
    if summary is None:
        raise NotFoundError(f"no permission found with id {permission_id}")
    return PermissionResponse.model_validate(summary)


# --- Register / Login -------------------------------------------------------


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, use_case: RegisterUseCase) -> RegisterResponse:
    output = await use_case.execute(
        RegisterUserInput(
            email=body.email,
            password=body.password,
            first_name=body.first_name,
            last_name=body.last_name,
        )
    )
    return RegisterResponse.model_validate(output)


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, use_case: LoginUseCase) -> LoginResponse:
    output = await use_case.execute(AuthenticateUserInput(email=body.email, password=body.password))
    return LoginResponse.model_validate(output)


# --- Users (read-only) -----------------------------------------------------


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: UUID, user_port: UserPort, current_user: CurrentUser) -> UserResponse:
    summary = await user_port.get_user_summary(user_id)
    if summary is None:
        raise NotFoundError(f"no user found with id {user_id}")
    response = UserResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


# --- Roles -------------------------------------------------------------------


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    body: CreateRoleRequest,
    use_case: CreateRoleUseCase,
    query_service: RoleQS,
    current_user: CurrentUser,
) -> RoleResponse:
    output = await use_case.execute(
        CreateRoleInput(
            organization_id=current_user.organization_id,
            **body.model_dump(),
            created_by=current_user.user_id,
        )
    )
    return await _get_role_response(output.role_id, query_service, current_user)


@router.get("/roles", response_model=PaginatedResponse[RoleResponse])
async def list_roles(
    query_service: RoleQS,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[RoleResponse]:
    summaries = await query_service.list_roles_for_organization(current_user.organization_id)
    items = [RoleResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"name", "is_active"}),
    )


@router.get("/roles/system", response_model=PaginatedResponse[RoleResponse])
async def list_system_roles(
    query_service: RoleQS, pagination: Pagination, sorting: Sorting, current_user: CurrentUser
) -> PaginatedResponse[RoleResponse]:
    # Registered before the parameterized "/roles/{role_id}" route below —
    # Starlette matches path templates in registration order, and both
    # have the same segment count, so "system" would otherwise be parsed
    # as (and fail validation as) a role_id UUID.
    summaries = await query_service.list_system_roles()
    items = [RoleResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"name", "is_active"}),
    )


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(role_id: UUID, query_service: RoleQS, current_user: CurrentUser) -> RoleResponse:
    return await _get_role_response(role_id, query_service, current_user)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID, use_case: DeleteRoleUseCase, current_user: CurrentUser
) -> None:
    await use_case.execute(DeleteRoleInput(role_id=role_id))


@router.patch("/roles/{role_id}/activate", response_model=RoleResponse)
async def activate_role(
    role_id: UUID, use_case: ActivateRoleUseCase, query_service: RoleQS, current_user: CurrentUser
) -> RoleResponse:
    await use_case.execute(ActivateRoleInput(role_id=role_id))
    return await _get_role_response(role_id, query_service, current_user)


@router.patch("/roles/{role_id}/deactivate", response_model=RoleResponse)
async def deactivate_role(
    role_id: UUID,
    use_case: DeactivateRoleUseCase,
    query_service: RoleQS,
    current_user: CurrentUser,
) -> RoleResponse:
    await use_case.execute(DeactivateRoleInput(role_id=role_id))
    return await _get_role_response(role_id, query_service, current_user)


@router.get("/roles/{role_id}/permissions", response_model=PaginatedResponse[PermissionResponse])
async def list_permissions_for_role(
    role_id: UUID,
    query_service: PermissionQS,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[PermissionResponse]:
    summaries = await query_service.list_permissions_for_role(role_id)
    items = [PermissionResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"code", "resource", "action"}),
    )


@router.post("/roles/{role_id}/permissions", response_model=PermissionResponse, status_code=201)
async def assign_permission_to_role(
    role_id: UUID,
    body: AssignPermissionToRoleRequest,
    use_case: AssignPermissionUseCase,
    query_service: PermissionQS,
    current_user: CurrentUser,
) -> PermissionResponse:
    output = await use_case.execute(
        AssignPermissionToRoleInput(
            role_id=role_id,
            permission_code=body.permission_code,
            granted_by=current_user.user_id,
        )
    )
    return await _get_permission_response(output.permission_id, query_service)


# --- Permissions ---------------------------------------------------------


@router.post("/permissions", response_model=PermissionResponse, status_code=201)
async def create_permission(
    body: CreatePermissionRequest,
    use_case: CreatePermissionUseCase,
    query_service: PermissionQS,
    current_user: CurrentUser,
) -> PermissionResponse:
    output = await use_case.execute(
        CreatePermissionInput(**body.model_dump(), created_by=current_user.user_id)
    )
    return await _get_permission_response(output.permission_id, query_service)


@router.get("/permissions/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: UUID, query_service: PermissionQS, current_user: CurrentUser
) -> PermissionResponse:
    return await _get_permission_response(permission_id, query_service)


@router.get("/permissions", response_model=PaginatedResponse[PermissionResponse])
async def list_permissions(
    query_service: PermissionQS,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[PermissionResponse]:
    summaries = await query_service.list_all_permissions()
    items = [PermissionResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"code", "resource", "action"}),
    )


# --- Role assignments ------------------------------------------------------


@router.post("/users/{user_id}/roles", response_model=RoleResponse, status_code=201)
async def assign_role_to_user(
    user_id: UUID,
    body: AssignRoleToUserRequest,
    use_case: AssignRoleUseCase,
    query_service: RoleQS,
    current_user: CurrentUser,
) -> RoleResponse:
    await use_case.execute(
        AssignRoleToUserInput(
            organization_id=current_user.organization_id,
            user_id=user_id,
            role_id=body.role_id,
            granted_by=current_user.user_id,
        )
    )
    return await _get_role_response(body.role_id, query_service, current_user)
