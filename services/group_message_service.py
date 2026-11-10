from sqlalchemy.ext.asyncio import AsyncSession
from models import GroupMessage, Server
from repositories.group_message_repository import GroupMessageRepository
from repositories.group_task_repository import GroupTaskRepository
from repositories.server_repository import ServerRepository
from schemas.group_message_schema import GroupMessageCreate, GroupMessageUpdate
from utils.enum import MessageType
from utils.exceptions import BadRequestError, NotFoundError

MAX_PAGE_SIZE = 100

# Member lang (kasama ang owner) ang makakabasa at makakapagpadala. Ang nagpadala lang ang makakapag-edit at makakapagbura.
class GroupMessageService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = GroupMessageRepository(db)
        self.servers = ServerRepository(db)
        self.tasks = GroupTaskRepository(db)  # group task, hindi ang personal na TaskRepository

    async def _check_member(self, user_id: int, server_id: int) -> Server:
        # None kung hindi owner o member: 404 din, para hindi malaman na may ganoong server
        server = await self.servers.get_server(server_id, user_id)
        if server is None:
            raise NotFoundError("Server not found")
        return server

    async def _get_own_message(self, user_id: int, server_id: int, message_id: int) -> GroupMessage:
        # wala, nabura na, sa iba, o nasa ibang server: 404 pareho, para hindi malaman kung may ganoong id
        message = await self.repo.get_own_message(user_id, server_id, message_id)
        if message is None:
            raise NotFoundError("Message not found")
        return message

    async def send_group_message(self, user_id: int, server_id: int, data: GroupMessageCreate) -> GroupMessage:
        await self._check_member(user_id, server_id)
        # dapat sa parehong server ang task na ina-attach (wala, nabura na, o sa ibang server: 404 pareho)
        if data.task_ref_id is not None and await self.tasks.get_task(server_id, data.task_ref_id) is None:
            raise NotFoundError("Task not found")
        return await self.repo.create_group_message(
            group_id=server_id,  # galing sa URL
            sender_id=user_id,  # galing sa naka-login na user, hindi sa request
            content=data.content,
            task_ref_id=data.task_ref_id,
            image_url=data.image_url,
            message_type=data.message_type,
        )

    async def get_group_messages(
        self, user_id: int, server_id: int, limit: int = 50, before_id: int | None = None
    ) -> list[GroupMessage]:
        await self._check_member(user_id, server_id)
        limit = max(1, min(limit, MAX_PAGE_SIZE))
        return await self.repo.get_group_messages(server_id, limit, before_id)

    async def edit_group_message(
        self, user_id: int, server_id: int, message_id: int, data: GroupMessageUpdate
    ) -> GroupMessage:
        await self._check_member(user_id, server_id)  # kapag umalis na sa server, hindi na puwede
        message = await self._get_own_message(user_id, server_id, message_id)
        if message.message_type != MessageType.TEXT:
            raise BadRequestError("Only text messages can be edited")
        if data.content == message.content:  # walang nagbago: huwag lagyan ng edited_at
            return message
        return await self.repo.update_content(message, data.content)

    async def delete_group_message(self, user_id: int, server_id: int, message_id: int) -> None:
        await self._check_member(user_id, server_id)
        message = await self._get_own_message(user_id, server_id, message_id)
        await self.repo.delete_message(message)

    async def get_recipient_ids(self, user_id: int, server_id: int) -> list[int]:
        """Mga user_id na dapat padalhan ng real-time na event (lahat ng member, kasama ang owner, maliban kay user_id)."""
        server = await self._check_member(user_id, server_id)
        members = await self.servers.get_server_members(server_id)
        return sorted(({m.user_id for m in members} | {server.owner_id}) - {user_id})
