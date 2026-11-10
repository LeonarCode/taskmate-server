import asyncio
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from config.settings import settings
from utils.exceptions import (
    UserNotFoundError, InvalidCredentialsError, EmailAlreadyExistsError,
    UsernameAlreadyExistsError, UnauthorizedError, InvalidResetCodeError
)
from utils.security import hash_password, verify_password, create_access_token
from repositories.user_repository import UserRepository
from repositories.password_reset_repository import PasswordResetRepository
from models.user import User
from schemas.user_schema import UserCreate, UserLogin, GoogleLogin, GoogleRegister, Token

# hash ng random na password na walang nakakaalam, panlaban sa timing attack (tingnan ang login)
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))

RESET_CODE_TTL = timedelta(minutes=10)
RESET_COOLDOWN = timedelta(seconds=60)  # pinakamaikling pagitan ng dalawang code para sa iisang user
RESET_MAX_ATTEMPTS = 5  # maling hula bawat code


def _hash_reset_code(user_id: int, code: str) -> str:
    # 6 digit lang ang code, kaya ang proteksyon ay ang bilis mag-expire at ang limitasyon ng hula, hindi ang hash
    return hmac.new(settings.SECRET_KEY.encode(), f"{user_id}:{code}".encode(), hashlib.sha256).hexdigest()


async def _verify_google_token(token: str) -> dict:
    """Ibabalik ang claims ng Google ID token (sub, email, name, picture...)."""
    try:
        # sync ang google-auth at may HTTP request para sa certs, kaya sa thread
        info = await asyncio.to_thread(
            google_id_token.verify_oauth2_token,
            token, google_requests.Request(), settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10,
        )
    except TransportError:
        raise  # hindi maabot ang Google, hindi mali ang token
    except (ValueError, GoogleAuthError) as e:  # mali, expired, ibang app, o maling issuer
        raise InvalidCredentialsError("Invalid Google token") from e
    if not (info.get("email") and info.get("email_verified")):
        raise UnauthorizedError("Google email is not verified")
    return info


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)
        self.resets = PasswordResetRepository(db)

    async def register(self, data: UserCreate) -> Token:
        email = data.email.lower()
        await self._raise_if_taken(email, data.username)
        password_hash = await asyncio.to_thread(hash_password, data.password)  # mabagal ang bcrypt, kaya sa thread
        user = await self._create_user(
            email=email,
            password=password_hash,
            fullname=data.fullname,
            username=data.username,
            age=data.age,
            user_type=data.user_type,
            organization=data.organization,
        )
        return Token(access_token=create_access_token(user.id))  # naka-login na agad pagkatapos ng Complete Setup

    async def login(self, data: UserLogin) -> Token:
        user = await self.repo.find_user_by_email(data.email.lower())
        # laging mag-verify, kahit walang user o Google-only, para pareho ang tagal ng sagot
        hashed = user.password if user and user.password else _DUMMY_HASH
        valid = await asyncio.to_thread(verify_password, data.password, hashed)
        if not (user and user.password and valid):
            raise InvalidCredentialsError("Invalid email or password")  # iisang mensahe para hindi malaman kung alin ang mali
        return Token(access_token=create_access_token(user.id))

    async def google_login(self, data: GoogleLogin) -> Token:
        info = await _verify_google_token(data.id_token)
        user = await self.repo.find_user_by_google_id(info["sub"])
        if user is None:
            # may email/password account na sa email na ito: huwag i-auto-link
            # (kahit sino ay puwedeng mag-signup gamit ang email ng iba, kaya mananatili sa kanya ang password)
            if await self.repo.find_user_by_email(info["email"].lower()):
                raise EmailAlreadyExistsError("Email is already registered, log in with your password")
            raise UserNotFoundError("No account for this Google user, register first")
        return Token(access_token=create_access_token(user.id))

    async def google_register(self, data: GoogleRegister) -> Token:
        info = await _verify_google_token(data.id_token)
        email, google_id = info["email"].lower(), info["sub"]
        await self._raise_if_taken(email, data.username, google_id)
        user = await self._create_user(
            email=email,
            password=None,
            google_id=google_id,
            fullname=data.fullname,
            username=data.username,
            age=data.age,
            user_type=data.user_type,
            organization=data.organization,
            photo_url=info.get("picture"),
        )
        return Token(access_token=create_access_token(user.id))

    async def forgot_password(self, email: str) -> tuple[str, str] | None:
        """Ibabalik ang (email, code) na dapat ipadala, o None kung walang ipapadala.

        Pareho ang sagot ng router kahit alin dito, para hindi malaman kung may account ang email."""
        user = await self.repo.find_user_by_email(email.lower())
        if user is None:
            return None
        now = datetime.now(timezone.utc)
        if await self.resets.has_recent(user.id, now - RESET_COOLDOWN):
            return None
        code = f"{secrets.randbelow(10**6):06d}"
        await self.resets.replace(user.id, _hash_reset_code(user.id, code), now + RESET_CODE_TTL)
        return user.email, code

    async def reset_password(self, email: str, code: str, new_password: str) -> None:
        user = await self.repo.find_user_by_email(email.lower())
        reset = await self.resets.get_active(user.id, datetime.now(timezone.utc)) if user else None
        if reset is None or reset.attempts >= RESET_MAX_ATTEMPTS:
            raise InvalidResetCodeError("Invalid or expired code")
        if not hmac.compare_digest(reset.code_hash, _hash_reset_code(user.id, code)):
            await self.resets.add_attempt(reset.id)
            raise InvalidResetCodeError("Invalid or expired code")  # iisang mensahe: mali, expired, o walang account
        user.password = await asyncio.to_thread(hash_password, new_password)
        await self.resets.delete_for_user(user.id)  # isang gamit lang ang code
        await self.db.commit()

    async def email_taken(self, email: str) -> bool:
        return await self.repo.find_user_by_email(email.lower()) is not None

    async def username_taken(self, username: str) -> bool:
        return await self.repo.find_user_by_username(username.strip().lower()) is not None

    async def _raise_if_taken(self, email: str, username: str, google_id: str | None = None) -> None:
        if google_id and await self.repo.find_user_by_google_id(google_id):
            raise EmailAlreadyExistsError("This Google account is already registered")
        if await self.repo.find_user_by_email(email):
            raise EmailAlreadyExistsError("Email is already registered")
        if await self.repo.find_user_by_username(username):
            raise UsernameAlreadyExistsError("Username is already taken")

    async def _create_user(self, **fields) -> User:
        try:
            return await self.repo.create_user(**fields)
        except IntegrityError:  # naunahan tayo ng ibang request (hal. dalawang beses na-tap)
            await self.db.rollback()
            await self._raise_if_taken(fields["email"], fields["username"], fields.get("google_id"))  # alamin kung alin ang duplicate
            raise
