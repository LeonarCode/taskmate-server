from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from utils.auth_dependency import get_current_user
from utils.connection_manager import manager
from models import User
from schemas.message_schema import MarkReadResponse
from schemas.notification_schema import NotificationResponse, UnreadCountResponse
from services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_notification_service(db: AsyncSession = Depends(get_db)) -> NotificationService:
    return NotificationService(db)


# Real-time: ang bagong notification ay itinutulak ng utils/realtime.py (push_notifications) sa /ws.
# Dito naman, ang mga pagbabago ng sarili mong notification ay ipinapaalam sa LAHAT ng device mo (kasama ang nag-request,
# ligtas ulitin), para magkapareho ang badge:
#   "notification_read" {"id"} · "notifications_read_all" {} · "notification_deleted" {"id"} · "notifications_cleared" {}


# Alerts tab: pinakabago muna; para sa mas luma, ipasa ang id ng pinakamatanda mong hawak bilang before_id
@router.get("", response_model=list[NotificationResponse])
async def view_notifications(
    limit: int = Query(50, ge=1, le=100),
    before_id: int | None = Query(None, gt=0),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
):
    return await service.get_notifications(current_user.id, limit, before_id, unread_only)


# Badge ng Alerts tab
@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
):
    return UnreadCountResponse(unread_count=await service.get_unread_count(current_user.id))


# "Mark all as read": ibinabalik kung ilan ang namarkahan
@router.post("/read-all", response_model=MarkReadResponse)
async def mark_all_read(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
):
    marked = await service.mark_all_read(current_user.id)
    if marked:
        background_tasks.add_task(manager.send_to_user, current_user.id, {"type": "notifications_read_all", "data": {}})
    return MarkReadResponse(marked_read=marked)


# Binuksan ang isang notification: ligtas ulitin. 404 kung wala o sa iba
@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    background_tasks: BackgroundTasks,
    notification_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
):
    notification = await service.mark_read(current_user.id, notification_id)
    background_tasks.add_task(
        manager.send_to_user, current_user.id, {"type": "notification_read", "data": {"id": notification_id}}
    )
    return notification


# Burahin ang isa (sa iyo lang)
@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    background_tasks: BackgroundTasks,
    notification_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
):
    await service.delete_notification(current_user.id, notification_id)
    background_tasks.add_task(
        manager.send_to_user, current_user.id, {"type": "notification_deleted", "data": {"id": notification_id}}
    )


# "Clear all": binubura ang lahat ng notification mo
@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_notifications(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
):
    cleared = await service.clear_all(current_user.id)
    if cleared:
        background_tasks.add_task(manager.send_to_user, current_user.id, {"type": "notifications_cleared", "data": {}})
