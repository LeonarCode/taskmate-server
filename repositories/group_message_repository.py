from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from models import GroupMessage

class GroupMessageRepository:
    """Walang pagsusuri ng member dito: ang service ang titingin muna (ServerRepository.get_server).
    Ang bawat method ay may server_id, kaya hindi makukuha ang mensahe ng ibang server."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_message_query(self, server_id: int):
        # lahat ng mensahe ng server, ng kahit sino (hindi lang ng user), hindi kasama ang nabura na;
        # kasama na ang nagpadala para magamit agad sa GroupMessageResponse (kung hindi, MissingGreenlet)
        return (
            select(GroupMessage)
            .options(selectinload(GroupMessage.sender))
            .where(GroupMessage.group_id == server_id, GroupMessage.is_deleted.is_(False))
        )

    async def _reload(self, message: GroupMessage) -> GroupMessage:
        # ang refresh ay nag-e-expire din ng sender, kaya ilo-load ulit para magamit agad sa GroupMessageResponse
        await self.db.refresh(message)
        await self.db.refresh(message, ["sender"])
        return message

    async def create_group_message(self, **data) -> GroupMessage:
        message = GroupMessage(**data)
        self.db.add(message)
        await self.db.commit()
        return await self._reload(message)

    async def get_group_messages(
        self, server_id: int, limit: int = 50, before_id: int | None = None
    ) -> list[GroupMessage]:
        # pinakabagong `limit` na mensahe, mula luma pataas; para sa mas luma, ipasa ang id ng pinakamatanda bilang before_id
        query = self._get_message_query(server_id)
        if before_id is not None:
            query = query.where(GroupMessage.id < before_id)
        # id ang panalo kapag pareho ang oras
        result = await self.db.scalars(
            query.order_by(GroupMessage.created_at.desc(), GroupMessage.id.desc()).limit(limit)
        )
        return list(reversed(result.all()))

    async def get_own_message(self, user_id: int, server_id: int, message_id: int) -> GroupMessage | None:
        # sa nagpadala lang, sa server na ito, at hindi pa nabubura
        return await self.db.scalar(
            self._get_message_query(server_id).where(
                GroupMessage.id == message_id, GroupMessage.sender_id == user_id
            )
        )

    async def update_content(self, message: GroupMessage, content: str) -> GroupMessage:
        message.content = content
        message.edited_at = datetime.now(timezone.utc)
        await self.db.commit()
        return await self._reload(message)

    async def delete_message(self, message: GroupMessage) -> None:
        message.is_deleted = True  # soft delete: nasa database pa, pero hindi na lalabas kahit saan
        await self.db.commit()
