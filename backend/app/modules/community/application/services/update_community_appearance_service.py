"""`UpdateCommunityAppearanceService` — sets a community's avatar/banner
image.

"Storage abstraction only" (this task's own MEDIA section) means this
service depends on `app.shared.application.storage_port.StoragePort` —
the same shared port `app.modules.documents` already built and wires
its own `LocalStorageProvider` implementation against — rather than
building a second, module-owned storage abstraction or a concrete new
backend. `Community.avatar_storage_path`/`banner_storage_path` store the
*key* `StoragePort.upload` returns, the same "entity stores a storage
key, not a resolved URL" shape `MedicalDocument.storage_path` already
establishes for itself; resolving a key to an actual displayable URL
(`StoragePort.get_presigned_url`, or a public CDN path for a real object
store) is a presentation-layer/deployment concern, not this service's.
"""

from io import BytesIO
from uuid import UUID

from app.modules.community.application.dto import (
    UpdateCommunityAppearanceInput,
    UpdateCommunityAppearanceOutput,
)
from app.modules.community.application.services._authorization import ensure_role_at_least
from app.modules.community.domain.enums import CommunityRole
from app.modules.community.domain.exceptions import CommunityMediaEmptyError, CommunityNotFoundError
from app.modules.community.domain.repositories import CommunityMemberRepository, CommunityRepository
from app.shared.application.storage_port import StoragePort
from app.shared.application.unit_of_work import UnitOfWork

_BUCKET = "community-media"


class UpdateCommunityAppearanceService:
    def __init__(
        self,
        *,
        community_repository: CommunityRepository,
        community_member_repository: CommunityMemberRepository,
        storage_port: StoragePort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._communities = community_repository
        self._members = community_member_repository
        self._storage = storage_port
        self._uow = unit_of_work

    async def execute(
        self, input_dto: UpdateCommunityAppearanceInput
    ) -> UpdateCommunityAppearanceOutput:
        community = await self._communities.get_by_id(input_dto.community_id)
        if community is None:
            raise CommunityNotFoundError(input_dto.community_id)

        member = await self._members.get_by_community_and_user(
            input_dto.community_id, input_dto.acting_user_id
        )
        ensure_role_at_least(
            member,
            CommunityRole.ADMIN,
            community_id=input_dto.community_id,
            user_id=input_dto.acting_user_id,
        )

        avatar_key = None
        if input_dto.avatar_data is not None:
            avatar_key = await self._upload(
                community_id=input_dto.community_id,
                field="avatar",
                data=input_dto.avatar_data,
                content_type=input_dto.avatar_content_type or "application/octet-stream",
                filename=input_dto.avatar_filename or "avatar",
            )
        banner_key = None
        if input_dto.banner_data is not None:
            banner_key = await self._upload(
                community_id=input_dto.community_id,
                field="banner",
                data=input_dto.banner_data,
                content_type=input_dto.banner_content_type or "application/octet-stream",
                filename=input_dto.banner_filename or "banner",
            )

        community.update_appearance(
            avatar_storage_path=avatar_key,
            clear_avatar=input_dto.clear_avatar,
            banner_storage_path=banner_key,
            clear_banner=input_dto.clear_banner,
        )

        await self._communities.add(community)
        self._uow.collect_events(community.pull_events())
        await self._uow.commit()

        return UpdateCommunityAppearanceOutput(
            community_id=community.id,
            avatar_storage_path=community.avatar_storage_path,
            banner_storage_path=community.banner_storage_path,
        )

    async def _upload(
        self, *, community_id: UUID, field: str, data: bytes, content_type: str, filename: str
    ) -> str:
        if not data:
            raise CommunityMediaEmptyError(field)
        object_name = f"{community_id}/{field}/{filename}"
        return await self._storage.upload(
            bucket=_BUCKET, object_name=object_name, data=BytesIO(data), content_type=content_type
        )
