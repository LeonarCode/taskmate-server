from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import GroupTask


class GroupTaskRepository:
    """Walang pagsusuri ng member dito. Ang service ang titingin muna kung member ng server ang user
    (ServerRepository.get_server), tapos saka tatawag dito. Kaya ang bawat method ay may server_id:
    hindi makukuha ang task ng ibang server kahit mahulaan ang task_id."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_server_task(self, **data) -> GroupTask:
        task = GroupTask(**data)
        self.db.add(task)  # walang await: sync ang add
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_task(self, server_id: int, task_id: int) -> GroupTask | None:
        return await self.db.scalar(
            select(GroupTask).where(
                GroupTask.id == task_id, GroupTask.server_id == server_id, GroupTask.is_deleted.is_(False)
            )
        )

    async def get_server_tasks(self, server_id: int) -> list[GroupTask]:
        result = await self.db.scalars(
            select(GroupTask)
            .where(GroupTask.server_id == server_id, GroupTask.is_deleted.is_(False))
            .order_by(GroupTask.deadline)
        )
        return list(result.all())

    async def update_task(self, server_id: int, task_id: int, **fields) -> GroupTask | None:
        task = await self.get_task(server_id, task_id)
        if task is None:
            return None
        for name, value in fields.items():
            setattr(task, name, value)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def mark_task_complete(self, server_id: int, task_id: int) -> GroupTask | None:
        task = await self.get_task(server_id, task_id)
        if task and not task.is_complete:
            task.is_complete = True
            task.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(task)
        return task

    async def mark_task_incomplete(self, server_id: int, task_id: int) -> GroupTask | None:
        task = await self.get_task(server_id, task_id)
        if task and task.is_complete:
            task.is_complete = False
            task.completed_at = None
            await self.db.commit()
            await self.db.refresh(task)
        return task

    async def delete_task(self, server_id: int, task_id: int) -> bool:
        # soft delete: hindi nawawala ang mga mensaheng nakaturo sa task na ito (GroupMessage.task_ref_id)
        task = await self.get_task(server_id, task_id)
        if task is None:
            return False
        task.is_deleted = True
        await self.db.commit()
        return True
