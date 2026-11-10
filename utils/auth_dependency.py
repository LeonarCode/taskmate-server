from fastapi import Depends, HTTPException, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from config.database import SessionLocal, get_db
from models.user import User
from repositories.user_repository import UserRepository
from utils.security import decode_access_token

bearer_scheme = HTTPBearer()  # walang header o hindi Bearer: 401 na agad


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = None
    user_id = decode_access_token(credentials.credentials)
    if user_id is not None:
        user = await UserRepository(db).find_user_by_id(user_id)
    if user is None:  # mali/expired ang token, o nabura na ang user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_user_ws(websocket: WebSocket) -> User | None:
    """Para sa WebSocket: ibabalik ang User, o None kung mali/expired ang token."""
    # Authorization header ang mas ligtas; ang ?token= ay fallback lang dahil lumalabas sa access log
    scheme, _, token = websocket.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        token = websocket.query_params.get("token", "")
    user_id = decode_access_token(token) if token else None
    if user_id is None:
        return None
    # sariling maikling session, hindi get_db: kung hindi, hawak ang DB connection habang bukas ang socket
    async with SessionLocal() as session:
        return await UserRepository(session).find_user_by_id(user_id)
