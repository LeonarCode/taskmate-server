from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, **data) -> User:
        user = User(**data)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def find_user_by_email(self, email: str) -> User | None:
        return await self.db.scalar(select(User).where(User.email == email))

    async def find_user_by_username(self, username: str) -> User | None:
        return await self.db.scalar(select(User).where(User.username == username))

    async def find_user_by_google_id(self, google_id: str) -> User | None:
        if not google_id:  # NULL ang google_id ng email/password users, huwag mag-match sa None
            return None
        return await self.db.scalar(select(User).where(User.google_id == google_id))

    async def find_user_by_id(self, user_id: int) -> User | None:
        return await self.db.get(User, user_id)

    async def find_users_by_ids(self, user_ids: list[int]) -> list[User]:
        if not user_ids:
            return []
        result = await self.db.scalars(select(User).where(User.id.in_(user_ids)))
        return list(result.all())

    async def search_users(self, prefix: str, exclude_id: int, limit: int = 20) -> list[User]:
        # nagsisimula sa prefix, hindi mahalaga ang laki ng letra; literal ang % at _ na tinype
        escaped = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        result = await self.db.scalars(
            select(User)
            .where(User.username.ilike(f"{escaped}%", escape="\\"), User.id != exclude_id)
            .order_by(User.username)
            .limit(limit)
        )
        return list(result.all())

    async def update_user(self, user: User, **fields) -> User:
        for name, value in fields.items():
            setattr(user, name, value)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    