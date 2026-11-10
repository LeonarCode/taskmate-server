from datetime import datetime, timezone
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.password_reset import PasswordReset


class PasswordResetRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def has_recent(self, user_id: int, since: datetime) -> bool:
        found = await self.db.scalar(
            select(PasswordReset.id).where(PasswordReset.user_id == user_id, PasswordReset.created_at > since).limit(1)
        )
        return found is not None

    async def get_active(self, user_id: int, now: datetime) -> PasswordReset | None:
        return await self.db.scalar(
            select(PasswordReset)
            .where(PasswordReset.user_id == user_id, PasswordReset.expires_at > now)
            .order_by(PasswordReset.id.desc())
            .limit(1)
        )

    async def replace(self, user_id: int, code_hash: str, expires_at: datetime) -> PasswordReset:
        # isang aktibong code lang bawat user: binubura ang dati
        await self.db.execute(delete(PasswordReset).where(PasswordReset.user_id == user_id))
        reset = PasswordReset(
            user_id=user_id, code_hash=code_hash, expires_at=expires_at, created_at=datetime.now(timezone.utc)
        )
        self.db.add(reset)
        await self.db.commit()
        await self.db.refresh(reset)
        return reset

    async def add_attempt(self, reset_id: int) -> None:
        # sa SQL mismo dinadagdagan, para tama ang bilang kahit sabay-sabay ang hula
        await self.db.execute(
            update(PasswordReset).where(PasswordReset.id == reset_id).values(attempts=PasswordReset.attempts + 1)
        )
        await self.db.commit()

    async def delete_for_user(self, user_id: int) -> None:
        # walang commit: ang tumatawag ang magko-commit, para isang transaction kasama ang pagpalit ng password
        await self.db.execute(delete(PasswordReset).where(PasswordReset.user_id == user_id))
