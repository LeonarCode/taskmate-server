import logging
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import SessionLocal
from models import Notification
from repositories.notification_repository import NotificationRepository
from utils.enum import NotifType
from utils.exceptions import BadRequestError, NotFoundError

logger = logging.getLogger(__name__)

MAX_PAGE_SIZE = 100
MAX_CONTENT = 255  # String(255) sa model

# Dalawang bahagi: ang notify / notify_many ay para sa ibang service (hal. kapag may sumali sa server),
# at ang iba ay para sa Alerts tab ng naka-login na user. Hindi gumagawa ng notification ang user para sa sarili o sa iba.
#
# Real-time: ang bawat nagawang notification ay naiipon sa self.created. Ang router ang kukuha (drain) pagkatapos ng request
# at itutulak sa socket gamit ang utils/realtime.push_notifications, kaya walang alam ang service sa WebSocket.
class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = NotificationRepository(db)
        self.created: list[Notification] = []

    def drain(self) -> list[Notification]:
        """Ibigay ang mga nagawang notification at linisin ang listahan (para hindi maitulak nang dalawang beses)."""
        created, self.created = self.created, []
        return created

    @staticmethod
    def _clean(content: str) -> str:
        content = content.strip()
        if not content:
            raise BadRequestError("Notification content is required")
        return content if len(content) <= MAX_CONTENT else content[: MAX_CONTENT - 1] + "…"

    @staticmethod
    def _check_reference(task_id: int | None, server_id: int | None, dm_id: int | None) -> None:
        if sum(x is not None for x in (task_id, server_id, dm_id)) > 1:
            raise BadRequestError("A notification can point to only one task, server or message")

    async def notify(
        self,
        user_id: int,
        content: str,
        notification_type: NotifType,
        *,
        task_id: int | None = None,
        server_id: int | None = None,
        dm_id: int | None = None,
    ) -> Notification:
        return (await self.notify_many([user_id], content, notification_type, task_id=task_id, server_id=server_id, dm_id=dm_id))[0]

    async def notify_many(
        self,
        user_ids: list[int],
        content: str,
        notification_type: NotifType,
        *,
        task_id: int | None = None,
        server_id: int | None = None,
        dm_id: int | None = None,
    ) -> list[Notification]:
        """Isa bawat user (walang doble), sa iisang transaction. Hal. lahat ng member ng server."""
        content = self._clean(content)
        self._check_reference(task_id, server_id, dm_id)
        if not user_ids:
            return []
        notifications = await self.repo.create_notifications(
            sorted(set(user_ids)), content, notification_type, task_id=task_id, server_id=server_id, dm_id=dm_id
        )
        self.created.extend(notifications)
        return notifications

    async def notify_many_safely(
        self,
        user_ids: list[int],
        content: str,
        notification_type: NotifType,
        *,
        task_id: int | None = None,
        server_id: int | None = None,
        dm_id: int | None = None,
    ) -> None:
        """Para sa mga producer: tapos na (at nai-commit na) ang tunay na ginawa ng user, kaya hindi dapat mabigo ang request
        dahil lang sa notification. Kapag may error, ilalagay sa log at hindi na ipapasa.

        Sa sarili itong maikling session ginagawa: kung mag-rollback ito sa session ng request, mag-e-expire ang lahat ng
        object doon (kasama ang current_user), at magka-MissingGreenlet ang router na gumagamit pa nito."""
        try:
            async with SessionLocal() as session:
                notifications = await NotificationService(session).notify_many(
                    user_ids, content, notification_type, task_id=task_id, server_id=server_id, dm_id=dm_id
                )
            self.created.extend(notifications)  # loaded na ang laman kahit sarado na ang session (expire_on_commit=False)
        except Exception:
            logger.exception("Failed to create notification: %s", content)

    async def get_notifications(
        self, user_id: int, limit: int = 50, before_id: int | None = None, unread_only: bool = False
    ) -> list[Notification]:
        limit = max(1, min(limit, MAX_PAGE_SIZE))
        return await self.repo.get_notifications(user_id, limit, before_id, unread_only)

    async def get_unread_count(self, user_id: int) -> int:
        return await self.repo.get_unread_count(user_id)

    async def _get_own(self, user_id: int, notification_id: int) -> Notification:
        # wala o sa iba: 404 pareho, para hindi malaman kung may ganoong id
        notification = await self.repo.get_notification(user_id, notification_id)
        if notification is None:
            raise NotFoundError("Notification not found")
        return notification

    async def mark_read(self, user_id: int, notification_id: int) -> Notification:
        notification = await self._get_own(user_id, notification_id)
        return await self.repo.mark_read(notification)  # ligtas ulitin: kung nabasa na, walang nagbabago

    async def mark_all_read(self, user_id: int) -> int:
        return await self.repo.mark_all_read(user_id)

    async def delete_notification(self, user_id: int, notification_id: int) -> None:
        await self.repo.delete_notification(await self._get_own(user_id, notification_id))

    async def clear_all(self, user_id: int) -> int:
        return await self.repo.delete_all(user_id)
