from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from models import Notification, Reference
from utils.enum import NotifType


class NotificationRepository:
    """Ang user_id ay laging bahagi ng hanap, kaya hindi makukuha o magagalaw ang notification ng iba."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _query(self, user_id: int):
        # kasama na ang reference para magamit agad sa NotificationResponse (kung hindi, MissingGreenlet)
        return (
            select(Notification)
            .options(selectinload(Notification.notification_reference))
            .where(Notification.user_id == user_id)
        )

    async def _get_or_create_reference(
        self, task_id: int | None, server_id: int | None, dm_id: int | None
    ) -> Reference | None:
        if task_id is None and server_id is None and dm_id is None:
            return None
        # iisang Reference para sa iisang tinutukoy, kahit ilang notification ang tumuturo (== None ay IS NULL)
        reference = await self.db.scalar(
            select(Reference).where(
                Reference.task_id == task_id, Reference.server_id == server_id, Reference.dm_id == dm_id
            ).limit(1)
        )
        if reference is None:
            reference = Reference(task_id=task_id, server_id=server_id, dm_id=dm_id)
            self.db.add(reference)
            await self.db.flush()  # para magkaroon ng id; ang commit ay kasama ng notification
        return reference

    async def create_notifications(
        self,
        user_ids: list[int],
        content: str,
        notification_type: NotifType,
        *,
        task_id: int | None = None,
        server_id: int | None = None,
        dm_id: int | None = None,
    ) -> list[Notification]:
        """Isang transaction para sa lahat ng user_ids."""
        reference = await self._get_or_create_reference(task_id, server_id, dm_id)
        notifications = [
            Notification(
                user_id=user_id,
                content=content,
                notification_type=notification_type,
                reference_id=reference.id if reference else None,
            )
            for user_id in user_ids
        ]
        self.db.add_all(notifications)
        await self.db.commit()
        if not notifications:
            return []
        # i-load ulit (kasama ang reference at created_at) sa isang query
        result = await self.db.scalars(
            select(Notification)
            .options(selectinload(Notification.notification_reference))
            .where(Notification.id.in_([n.id for n in notifications]))
            .order_by(Notification.id)
            .execution_options(populate_existing=True)
        )
        return list(result.all())

    async def get_notifications(
        self, user_id: int, limit: int = 50, before_id: int | None = None, unread_only: bool = False
    ) -> list[Notification]:
        # pinakabago muna; para sa mas luma, ipasa ang id ng pinakamatanda mong hawak bilang before_id
        query = self._query(user_id)
        if unread_only:
            query = query.where(Notification.is_read.is_(False))
        if before_id is not None:
            query = query.where(Notification.id < before_id)
        result = await self.db.scalars(query.order_by(Notification.id.desc()).limit(limit))
        return list(result.all())

    async def get_notification(self, user_id: int, notification_id: int) -> Notification | None:
        return await self.db.scalar(self._query(user_id).where(Notification.id == notification_id))

    async def get_unread_count(self, user_id: int) -> int:
        return await self.db.scalar(
            select(func.count()).select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        ) or 0

    async def mark_read(self, notification: Notification) -> Notification:
        if not notification.is_read:
            notification.is_read = True
            await self.db.commit()
        return notification

    async def mark_all_read(self, user_id: int) -> int:
        result = await self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        await self.db.commit()
        return result.rowcount

    async def delete_notification(self, notification: Notification) -> None:
        await self.db.delete(notification)
        await self.db.commit()

    async def delete_all(self, user_id: int) -> int:
        result = await self.db.execute(delete(Notification).where(Notification.user_id == user_id))
        await self.db.commit()
        return result.rowcount
