from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from models import Task
from repositories.task_repository import TaskRepository
from schemas.task_schema import TaskCreate, TaskUpsert
from utils.enum import TaskPriority
from utils.exceptions import NotFoundError

class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TaskRepository(db)

    async def task_create(self, user_id: int, data: TaskCreate) -> Task:
        return await self.repo.create_task(
            uid=user_id,
            title=data.title,
            description=data.description,
            priority=TaskPriority(data.priority),
            deadline=data.deadline,
            has_alarm=data.has_alarm,
            client_id=str(uuid4()),  # para walang task na walang client_id
        )

    async def task_upsert(self, user_id: int, client_id: UUID, data: TaskUpsert) -> Task:
        # ang app ang nakakaalam kung kailan tinik ang task (maaaring offline), kaya galing sa kanya ang completed_at
        completed_at = (data.completed_at or datetime.now(timezone.utc)) if data.is_complete else None
        task = await self.repo.upsert_by_client_id(
            user_id,
            str(client_id),
            title=data.title,
            description=data.description,
            priority=data.priority,
            deadline=data.deadline,
            has_alarm=data.has_alarm,
            is_complete=data.is_complete,
            completed_at=completed_at,
            is_synced=True,
        )
        if task is None:  # nabura na ito; hindi ito ibabalik ng lumang device
            raise NotFoundError("Task not found")
        return task

    async def task_delete_by_client_id(self, user_id: int, client_id: UUID) -> None:
        await self.repo.soft_delete_by_client_id(user_id, str(client_id))

    async def task_view(self, user_id: int) -> list[Task]:
        return await self.repo.view_by_user(user_id)

    async def mark_task_complete(self, user_id: int, task_id: int) -> Task:
        task = await self.repo.mark_task_complete(user_id, task_id)
        if task is None:  # wala, o hindi sa kanya (404 pareho para hindi malaman kung may ganoong id)
            raise NotFoundError("Task not found")
        return task

    async def mark_task_incomplete(self, user_id: int, task_id: int) -> Task:
        task = await self.repo.mark_task_incomplete(user_id, task_id)
        if task is None:
            raise NotFoundError("Task not found")
        return task

    async def task_delete(self, user_id: int, task_id: int) -> None:
        if not await self.repo.delete_task(user_id, task_id):
            raise NotFoundError("Task not found")
