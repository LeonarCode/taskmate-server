from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models import Task


class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task(self, **data) -> Task:
        task = Task(**data)
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def _find_by_client_id(self, user_id: int, client_id: str) -> Task | None:
        # kasama ang soft-deleted; ang user_id ay laging bahagi ng hanap
        return await self.db.scalar(select(Task).where(Task.uid == user_id, Task.client_id == client_id))

    async def upsert_by_client_id(self, user_id: int, client_id: str, **fields) -> Task | None:
        """Gumawa o i-update ayon sa UUID ng app. None kung nabura na ang task (ang bura ang panalo)."""
        task = await self._find_by_client_id(user_id, client_id)
        if task is None:
            try:
                return await self.create_task(uid=user_id, client_id=client_id, **fields)
            except IntegrityError:  # naunahan ng parehong request na sabay dumating
                await self.db.rollback()
                task = await self._find_by_client_id(user_id, client_id)
                if task is None:
                    raise
        if task.is_deleted:
            return None
        for name, value in fields.items():
            setattr(task, name, value)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def soft_delete_by_client_id(self, user_id: int, client_id: str) -> None:
        # walang error kapag wala o nabura na: pareho ang kalalabasan, kaya ligtas ulitin ng sync
        task = await self._find_by_client_id(user_id, client_id)
        if task is not None and not task.is_deleted:
            task.is_deleted = True
            await self.db.commit()

    async def get_task(self, user_id: int, task_id: int) -> Task | None:
        # laging kasama ang user_id para hindi magalaw ang task ng ibang user
        return await self.db.scalar(
            select(Task).where(Task.id == task_id, Task.uid == user_id, Task.is_deleted.is_(False))
        )

    async def view_by_user(self, user_id: int) -> list[Task]:
        result = await self.db.scalars(
            select(Task).where(Task.uid == user_id, Task.is_deleted.is_(False)).order_by(Task.deadline)
        )
        return list(result.all())

    async def find_task_by_status(self, user_id: int, is_complete: bool) -> list[Task]:
        result = await self.db.scalars(
            select(Task)
            .where(Task.uid == user_id, Task.is_deleted.is_(False), Task.is_complete.is_(is_complete))
            .order_by(Task.deadline)
        )
        return list(result.all())

    async def delete_task(self, user_id: int, task_id: int) -> bool:
        task = await self.get_task(user_id, task_id)
        if task is None:
            return False
        await self.db.delete(task)
        await self.db.commit()
        return True

    async def mark_task_complete(self, user_id: int, task_id: int) -> Task | None:
        task = await self.get_task(user_id, task_id)
        if task and not task.is_complete:
            task.is_complete = True
            task.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(task)
        return task

    async def mark_task_incomplete(self, user_id: int, task_id: int) -> Task | None:
        task = await self.get_task(user_id, task_id)
        if task and task.is_complete:
            task.is_complete = False
            task.completed_at = None
            await self.db.commit()
            await self.db.refresh(task)
        return task
