import base64
import binascii
import hashlib
import re
from fastapi import APIRouter, Depends, File, Path, Query, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from utils.auth_dependency import get_current_user
from utils.exceptions import NotFoundError
from models import User
from repositories.user_repository import UserRepository
from schemas.user_schema import ProfileUpdate, UserPublic, UserResponse
from services.user_service import MAX_PHOTO_BYTES, UserService

router = APIRouter(prefix="/users", tags=["users"])

# raster lang (walang svg: puwedeng may script kapag binuksan sa browser)
_DATA_URL = re.compile(r"^data:(image/(?:jpeg|png|webp|gif));base64,(.+)$", re.DOTALL)


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


# Chats tab, "+": hanapin ang user sa username para makapagsimula ng usapan (nagsisimula sa tinype, kasama ang "@").
# Hindi kasama ang sarili. Walang laman na hanap: walang resulta
@router.get("/search", response_model=list[UserPublic])
async def search_users(
    q: str = Query(max_length=255),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    return await service.search_users(current_user.id, q, limit)


# Edit Profile: full name, age, user type (at organization). Ang ipinadala lang ang nababago
@router.patch("/me", response_model=UserResponse)
async def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    return await service.update_profile(current_user.id, data)


# Bagong larawan: multipart/form-data na may field na "file" (jpeg, png, webp o gif; hanggang 5 MB). Ibinabalik ang buong profile.
# Kung may CLOUDINARY_URL, sa Cloudinary itatabi at https URL ang magiging photo_url; kung wala, sa database (dev lang).
# 400 kapag hindi larawan o walang laman, 413 "file_too_large" kapag lampas sa limit,
# 503 "storage_unavailable" kapag hindi maabot ang Cloudinary: puwedeng subukan ulit
@router.put("/me/photo", response_model=UserResponse)
async def upload_photo(
    file: UploadFile = File(),
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    content = await file.read(MAX_PHOTO_BYTES + 1)  # isang byte na sobra lang para malaman na lampas, hindi ang buong file
    return await service.set_photo(current_user.id, content)


# Larawan ng isang user (para sa listahan ng usapan at members). Mag-send ng Authorization header sa Image.network
@router.get("/{user_id}/photo")
async def user_photo(
    request: Request,
    user_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await UserRepository(db).find_user_by_id(user_id)
    photo = user.photo_url if user else None
    if not photo:
        raise NotFoundError("No photo")
    match = _DATA_URL.match(photo)
    if match:
        try:
            content = base64.b64decode(match.group(2), validate=True)
        except (binascii.Error, ValueError):
            raise NotFoundError("No photo")
        etag = f'"{hashlib.sha256(content).hexdigest()[:32]}"'
        headers = {"ETag": etag, "Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"}
        if request.headers.get("if-none-match") == etag:  # hindi pa nagbago: huwag nang ipadala ulit
            return Response(status_code=304, headers=headers)
        return Response(content=content, media_type=match.group(1), headers=headers)
    if photo.startswith("https://"):  # hal. larawan mula sa Google
        return RedirectResponse(photo, status_code=302)
    raise NotFoundError("No photo")
