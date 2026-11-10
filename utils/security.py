from datetime import datetime, timedelta, timezone
import jwt
from bcrypt import checkpw, gensalt, hashpw

from config.settings import settings

def hash_password(password: str) -> str:
    # hashpw nagra-raise ng ValueError kapag lampas 72 bytes ang password
    # bagong random salt bawat password; kasama na sa hash ang salt
    hashed = hashpw(password.encode("utf-8"), gensalt())
    return hashed.decode("utf-8")

def verify_password(password: str, hashed: str | None) -> bool:
    if not hashed:  # Google-only user, walang password
        return False
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:  # checkpw nagra-raise kapag lampas 72 bytes
        return False
    return checkpw(password_bytes, hashed.encode("utf-8"))

def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),  # dapat string
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> int | None:
    """Ibabalik ang user_id, o None kung invalid/expired ang token."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None