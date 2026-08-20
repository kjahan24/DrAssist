"""`RegisterUser` — self-service account creation for the current
frontend's Sign Up page (`POST /auth/register`).

**Why this provisions a brand new organization for every registration**:
this module's own domain model requires every `User.organization_id` to
be non-null (see `domain/entities.py`), but the frontend's Sign Up form
(`frontend/src/app/(auth)/register/page.tsx`) collects only a full name,
email, and password — no organization field, no invite code, no "join an
existing tenant" affordance anywhere in the current UI. The only
interpretation consistent with what the frontend actually sends is the
common early-stage-SaaS shape: signing up provisions the user's own new
tenant, with them as its first user. This reuses the Organization
module's own already-built `CreateOrganization` use case through its
public `OrganizationProvisioningPort` (`app.modules.organization.public
.interfaces`) — added by this same task, narrowly, for exactly this call
site — never that module's internals.

**Why email must be globally unique, not just per-organization**: since
every registration mints a fresh organization, a per-organization
uniqueness check (`UserRepository.get_by_email`) can never fire — the org
is brand new, so no prior user of it can exist. A caller resubmitting (or
an attacker probing) the same email would otherwise silently create a
second, disconnected account+tenant for it every time. `AuthenticateUser`
needs the same global lookup to sign a user in from email alone (it also
has no organization field), so both use cases share
`UserRepository.get_by_email_any_organization` — see that abstract
method's own docstring, and the `uq_users_email_global` migration that
backs it as a real database constraint, not just this use case's
check-then-act.

**Why the user is activated immediately**: `User.status` defaults to
`UserStatus.INVITED` (see `domain/entities.py`), and `can_authenticate()`
requires `ACTIVE`. This task's scope is register + login only — no
email-verification-confirmation endpoint exists to ever transition a
user out of `INVITED` — so leaving a freshly registered user at `INVITED`
would make them permanently unable to log in. `RegisterUser` therefore
calls `user.activate()` immediately after `User.register()`. The
frontend's own post-register redirect to `/verify-email` remains a
harmless, purely informational screen today — a future task can wire a
real verification flow without this use case needing to change.
"""

from app.core.security.password_hashing import hash_password
from app.modules.authentication.application.dto import RegisterUserInput, RegisterUserOutput
from app.modules.authentication.domain.entities import User
from app.modules.authentication.domain.exceptions import DuplicateEmailError
from app.modules.authentication.domain.repositories import UserRepository
from app.modules.authentication.domain.value_objects import HashedPassword
from app.modules.organization.public.interfaces import OrganizationProvisioningPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase
from app.shared.domain.common_value_objects import EmailAddress


class RegisterUser(UseCase[RegisterUserInput, RegisterUserOutput]):
    def __init__(
        self,
        *,
        user_repository: UserRepository,
        organization_provisioning_port: OrganizationProvisioningPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._users = user_repository
        self._organizations = organization_provisioning_port
        self._uow = unit_of_work

    async def execute(self, input_dto: RegisterUserInput) -> RegisterUserOutput:
        email = EmailAddress(input_dto.email)

        existing = await self._users.get_by_email_any_organization(email)
        if existing is not None:
            raise DuplicateEmailError(str(email))

        organization = await self._organizations.provision_organization(
            name=f"{input_dto.first_name} {input_dto.last_name}'s Organization",
            email=str(email),
        )

        user = User.register(
            organization_id=organization.organization_id,
            email=email,
            password_hash=HashedPassword(hash_password(input_dto.password)),
            first_name=input_dto.first_name,
            last_name=input_dto.last_name,
        )
        user.activate()
        await self._users.add(user)

        self._uow.collect_events(user.pull_events())
        await self._uow.commit()

        return RegisterUserOutput(
            user_id=user.id, organization_id=user.organization_id, email=str(user.email)
        )
