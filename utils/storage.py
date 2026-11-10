import asyncio
import io
import logging
from urllib.parse import unquote, urlparse
import cloudinary.uploader
from config.settings import settings
from utils.exceptions import StorageError

logger = logging.getLogger("taskmate.storage")


def is_configured() -> bool:
    return bool(settings.CLOUDINARY_URL)


def _credentials() -> dict:
    # cloudinary://API_KEY:API_SECRET@CLOUD_NAME (ang mga espesyal na character sa secret ay naka-%encode)
    url = urlparse(settings.CLOUDINARY_URL or "")
    credentials = {
        "cloud_name": url.hostname,
        "api_key": unquote(url.username or ""),
        "api_secret": unquote(url.password or ""),
    }
    if url.scheme != "cloudinary" or not all(credentials.values()):
        raise StorageError("CLOUDINARY_URL must look like cloudinary://API_KEY:API_SECRET@CLOUD_NAME")
    return credentials


def _upload_sync(file: io.BytesIO, **options) -> str:
    result = cloudinary.uploader.upload(file, **_credentials(), secure=True, resource_type="image", **options)
    return result["secure_url"]


async def upload_avatar(user_id: int, content: bytes) -> str:
    """Ilipat ang larawan (bytes ng file) sa Cloudinary at ibalik ang https URL nito.

    Iisang public_id bawat user at overwrite, kaya napapalitan ang dating larawan (walang naiiwang luma), at ang bagong URL
    ay may bagong version kaya hindi naka-cache ang luma. Hanggang 512x512 lang ang itatabi."""
    try:
        return await asyncio.to_thread(  # sync ang SDK at may HTTP request, kaya sa thread
            _upload_sync,
            io.BytesIO(content),
            public_id=f"taskmate/avatars/{user_id}",
            overwrite=True,
            invalidate=True,
            transformation=[{"width": 512, "height": 512, "crop": "limit"}],
        )
    except StorageError:
        logger.error("CLOUDINARY_URL is malformed")
        raise
    except Exception as e:
        logger.exception("Cloudinary upload failed for user %s", user_id)
        raise StorageError("Image storage is unavailable, try again") from e
