from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from models import GroupTask, Server
from repositories.group_task_repository import GroupTaskRepository
from repositories.server_repository import ServerRepository
from repositories.user_repository import UserRepository
from schemas.group_task_schema import GroupTaskCreate, GroupTaskUpdate
from services.notification_service import NotificationService
from utils.enum import NotifType, TaskPriority
from utils.exceptions import ForbiddenError, NotFoundError

# Owner: lahat. Member: makita ang mga task at mag-mark as completed lang.
class GroupTaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = GroupTaskRepository(db)
        self.servers = ServerRepository(db)
        self.users = UserRepository(db)
        self.notifications = NotificationService(db)

    def drain_notifications(self):
        """Mga nagawang notification ng request na ito, para itulak ng router sa socket (utils/realtime.push_notifications)."""
        return self.notifications.drain()

    async def _check_member(self, user_id: int, server_id: int) -> Server:
        # None kung hindi owner o member: 404 din, para hindi malaman na may ganoong server
        server = await self.servers.get_server(server_id, user_id)
        if server is None:
            raise NotFoundError("Server not found")
        return server

    async def _check_owner(self, user_id: int, server_id: int) -> Server:
        server = await self._check_member(user_id, server_id)
        if server.owner_id != user_id:  # member lang siya
            raise ForbiddenError("Only the server owner can do this")
        return server

    async def _display_name(self, user_id: int) -> str:
        user = await self.users.find_user_by_id(user_id)
        return (user.fullname or user.username) if user else "Someone"

    @staticmethod
    def _found(task: GroupTask | None) -> GroupTask:
        if task is None:  # wala, nabura na, o nasa ibang server
            raise NotFoundError("Task not found")
        return task

    async def create_group_task(self, user_id: int, server_id: int, data: GroupTaskCreate) -> GroupTask:
        server = await self._check_owner(user_id, server_id)
        task = await self.repo.create_server_task(
            server_id = server_id,
            title = data.title,
            description = data.description,
            priority = TaskPriority(data.priority),
            deadline = data.deadline,
            has_alarm = data.has_alarm,
            client_id =str(uuid4())
        )
        # abisuhan ang mga member (hindi ang may-ari na gumawa nito)
        member_ids = [m.user_id for m in await self.servers.get_server_members(server_id) if m.user_id != user_id]
        await self.notifications.notify_many_safely(
            member_ids, f"New task in {server.name}: {task.title}", NotifType.SERVER_ACTIVITY, server_id = server_id
        )
        return task

    async def view_group_tasks(self, user_id: int, server_id: int) -> list[GroupTask]:
        await self._check_member(user_id, server_id)
        return await self.repo.get_server_tasks(server_id)

    async def update_group_task(
        self, user_id: int, server_id: int, task_id: int, data: GroupTaskUpdate
    ) -> GroupTask:
        await self._check_owner(user_id, server_id)
        return self._found(await self.repo.update_task(server_id, task_id, **data.model_dump(exclude_unset=True)))

    async def mark_task_complete(self, user_id: int, server_id: int, task_id: int) -> GroupTask:
        server = await self._check_member(user_id, server_id)  # kahit sinong member
        was_complete = self._found(await self.repo.get_task(server_id, task_id)).is_complete
        task = self._found(await self.repo.mark_task_complete(server_id, task_id))
        # abisuhan ang may-ari kapag member ang nag-complete, sa unang beses lang (ligtas ulitin ang complete)
        if was_complete or user_id == server.owner_id:
            return task
        name = await self._display_name(user_id)
        await self.notifications.notify_many_safely(
            [server.owner_id],
            f'{name} completed "{task.title}" in {server.name}',
            NotifType.SERVER_ACTIVITY,
            server_id = server_id,
        )
        return task

    async def mark_task_incomplete(self, user_id: int, server_id: int, task_id: int) -> GroupTask:
        await self._check_owner(user_id, server_id)  # owner lang ang makakapag-undo
        return self._found(await self.repo.mark_task_incomplete(server_id, task_id))

    async def delete_group_task(self, user_id: int, server_id: int, task_id: int) -> None:
        await self._check_owner(user_id, server_id)
        if not await self.repo.delete_task(server_id, task_id):
            raise NotFoundError("Task not found")
