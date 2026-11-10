from sqlalchemy.ext.asyncio import AsyncSession
from models import Message
from repositories.message_repository import MessageRepository
from repositories.task_repository import TaskRepository
from repositories.user_repository import UserRepository
from schemas.message_schema import MessageCreate, MessageResponse, MessageUpdate, ConversationResponse
from schemas.user_schema import UserPublic
from utils.enum import MessageType
from utils.exceptions import BadRequestError, NotFoundError

MAX_PAGE_SIZE = 100

class MessageService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = MessageRepository(db)
        self.users = UserRepository(db)
        self.tasks = TaskRepository(db)

    async def send_message(self, sender_id: int, receiver_id: int, data: MessageCreate) -> Message:
        if sender_id == receiver_id:
            raise BadRequestError("You cannot message yourself")
        if await self.users.find_user_by_id(receiver_id) is None:
            raise NotFoundError("User not found")
        # dapat sa sender ang task na ina-attach (wala, nabura na, o sa iba: 404 pareho)
        if data.task_ref_id is not None and await self.tasks.get_task(sender_id, data.task_ref_id) is None:
            raise NotFoundError("Task not found")
        return await self.repo.create_message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=data.content,
            task_ref_id=data.task_ref_id,
            image_url=data.image_url,
            message_type=data.message_type,
        )

    async def get_messages(
        self, user_id: int, other_user_id: int, limit: int = 50, before_id: int | None = None
    ) -> list[Message]:
        limit = max(1, min(limit, MAX_PAGE_SIZE))
        return await self.repo.get_messages(user_id, other_user_id, limit, before_id)

    async def _get_own_message(self, user_id: int, other_user_id: int, message_id: int) -> Message:
        # wala, nabura na, sa iba, o sa ibang usapan: 404 pareho, para hindi malaman kung may ganoong id
        message = await self.repo.get_own_message(user_id, other_user_id, message_id)
        if message is None:
            raise NotFoundError("Message not found")
        return message

    async def edit_message(self, user_id: int, other_user_id: int, message_id: int, data: MessageUpdate) -> Message:
        message = await self._get_own_message(user_id, other_user_id, message_id)
        if message.message_type != MessageType.TEXT:
            raise BadRequestError("Only text messages can be edited")
        if data.content == message.content:  # walang nagbago: huwag lagyan ng edited_at
            return message
        return await self.repo.update_content(message, data.content)

    async def delete_message(self, user_id: int, other_user_id: int, message_id: int) -> None:
        message = await self._get_own_message(user_id, other_user_id, message_id)
        await self.repo.delete_message(message)

    async def get_conversations(self, user_id: int) -> list[ConversationResponse]:
        last_messages = await self.repo.get_conversations(user_id)
        if not last_messages:
            return []
        unread = await self.repo.get_unread_counts(user_id)
        partner_ids = {m.receiver_id if m.sender_id == user_id else m.sender_id for m in last_messages}
        partners = {u.id: u for u in await self.users.find_users_by_ids(list(partner_ids))}  # isang query lang
        conversations = []
        for message in last_messages:
            partner_id = message.receiver_id if message.sender_id == user_id else message.sender_id
            conversations.append(ConversationResponse(
                partner=UserPublic.model_validate(partners[partner_id]),
                last_message=MessageResponse.model_validate(message),
                unread_count=unread.get(partner_id, 0),
            ))
        return conversations

    async def mark_read(self, user_id: int, other_user_id: int) -> int:
        return await self.repo.mark_conversation_read(user_id, other_user_id)
