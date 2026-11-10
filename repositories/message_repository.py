from datetime import datetime, timezone
from sqlalchemy import case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from models import Message

class MessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_message_query(self, user_id: int, other_user_id: int):
        # hindi kasama ang nabura na (is_deleted)
        return select(Message).where(
            ((Message.sender_id == user_id) & (Message.receiver_id == other_user_id))
            | ((Message.sender_id == other_user_id) & (Message.receiver_id == user_id)),
            Message.is_deleted.is_(False),
        )

    async def create_message(self, **data) -> Message:
        message = Message(**data)
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_messages(
        self, user_id: int, other_user_id: int, limit: int = 50, before_id: int | None = None
    ) -> list[Message]:
        # pinakabagong `limit` na mensahe, mula luma pataas; para sa mas luma, ipasa ang id ng pinakamatanda bilang before_id
        query = self._get_message_query(user_id, other_user_id)
        if before_id is not None:
            query = query.where(Message.id < before_id)
        # id ang panalo kapag pareho ang oras
        result = await self.db.scalars(query.order_by(Message.created_at.desc(), Message.id.desc()).limit(limit))
        return list(reversed(result.all()))

    async def get_own_message(self, user_id: int, other_user_id: int, message_id: int) -> Message | None:
        # sa nagpadala lang, sa usapang ito (kay other_user_id), at hindi pa nabubura
        return await self.db.scalar(
            select(Message).where(
                Message.id == message_id,
                Message.sender_id == user_id,
                Message.receiver_id == other_user_id,
                Message.is_deleted.is_(False),
            )
        )

    async def update_content(self, message: Message, content: str) -> Message:
        message.content = content
        message.edited_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def delete_message(self, message: Message) -> None:
        message.is_deleted = True  # soft delete: nasa database pa, pero hindi na lalabas kahit saan
        await self.db.commit()

    async def get_conversations(self, user_id: int) -> list[Message]:
        # huling mensahe (na hindi nabura) sa bawat kausap, pinakabago muna
        partner = case((Message.sender_id == user_id, Message.receiver_id), else_=Message.sender_id)
        latest_ids = (
            select(func.max(Message.id))
            .where(or_(Message.sender_id == user_id, Message.receiver_id == user_id), Message.is_deleted.is_(False))
            .group_by(partner)
        )
        result = await self.db.scalars(
            select(Message).where(Message.id.in_(latest_ids)).order_by(Message.id.desc())
        )
        return list(result.all())

    async def get_unread_counts(self, user_id: int) -> dict[int, int]:
        # {sender_id: bilang ng hindi pa nababasa}; hindi kasama ang nabura
        result = await self.db.execute(
            select(Message.sender_id, func.count())
            .where(Message.receiver_id == user_id, Message.is_read.is_(False), Message.is_deleted.is_(False))
            .group_by(Message.sender_id)
        )
        return {sender_id: count for sender_id, count in result.all()}

    async def mark_conversation_read(self, user_id: int, other_user_id: int) -> int:
        # ang mga mensaheng natanggap lang ni user_id ang namamarkahan; ibabalik kung ilan
        result = await self.db.execute(
            update(Message)
            .where(
                Message.receiver_id == user_id,
                Message.sender_id == other_user_id,
                Message.is_read.is_(False),
                Message.is_deleted.is_(False),
            )
            .values(is_read=True)
        )
        await self.db.commit()
        return result.rowcount
