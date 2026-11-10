import base64
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from repositories.user_repository import UserRepository
from schemas.user_schema import ProfileUpdate
from utils import storage
from utils.exceptions import BadRequestError, FileTooLargeError, NotFoundError
from utils.images import detect_image_type

MAX_SEARCH_RESULTS = 50
MAX_PHOTO_BYTES = 5 * 1024 * 1024  # pinakamalaking larawang tatanggapin (kinukuha ng app ang ~200 KB pagkatapos mag-compress)
LOCAL_PHOTO_MAX_BYTES = 600_000  # kung walang Cloudinary: ~800k na character kapag naging data URL, tulad ng dating limit

class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    async def _get(self, user_id: int) -> User:
        user = await self.repo.find_user_by_id(user_id)
        if user is None:  # nabura ang account habang may hawak pang token
            raise NotFoundError("User not found")
        return user

    async def update_profile(self, user_id: int, data: ProfileUpdate) -> User:
        user = await self._get(user_id)
        fields = data.model_dump(exclude_unset=True)
        if not fields:  # walang ipinadala, walang babaguhin
            return user
        return await self.repo.update_user(user, **fields)

    async def set_photo(self, user_id: int, content: bytes) -> User:
        """content ay ang bytes ng na-upload na file (hanggang MAX_PHOTO_BYTES + 1, para malaman kung lampas)."""
        if len(content) > MAX_PHOTO_BYTES:
            raise FileTooLargeError(f"Photo is too large (max {MAX_PHOTO_BYTES // (1024 * 1024)} MB)")
        if not content:
            raise BadRequestError("Photo is empty")
        kind = detect_image_type(content)  # ang laman mismo ang tinitingnan, hindi ang sinasabi ng client
        if kind is None:
            raise BadRequestError("Photo must be a jpeg, png, webp or gif image")
        user = await self._get(user_id)
        if storage.is_configured():
            photo_url = await storage.upload_avatar(user_id, content)  # https URL na lang ang itatabi, hindi ang buong larawan
        else:
            # dev lang: walang Cloudinary, kaya sa database itatabi bilang data URL (iyon ang binabasa ng GET /users/{id}/photo)
            if len(content) > LOCAL_PHOTO_MAX_BYTES:
                raise FileTooLargeError(f"Photo is too large for local storage (max {LOCAL_PHOTO_MAX_BYTES // 1000} KB)")
            photo_url = f"data:image/{kind};base64," + base64.b64encode(content).decode()
        return await self.repo.update_user(user, photo_url=photo_url)

    async def search_users(self, user_id: int, query: str, limit: int = 20) -> list[User]:
        # ang "@leo" ay "leo": ganoon ipinapakita ang username sa app. Ang sarili ay hindi kasama
        query = query.strip().lstrip("@").strip()
        if not query:
            return []
        return await self.repo.search_users(query, user_id, max(1, min(limit, MAX_SEARCH_RESULTS)))
