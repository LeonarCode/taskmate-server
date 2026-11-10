from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from utils.auth_dependency import get_current_user
from utils.connection_manager import manager
from models import User
from schemas.message_schema import (
    MessageCreate, MessageResponse, MessageUpdate, ConversationResponse, MarkReadResponse
)
from services.message_service import MessageService

router = APIRouter(prefix="/messages", tags=["messages"])

def get_message_service(db: AsyncSession = Depends(get_db)) -> MessageService:
    return MessageService(db)


# Chats tab: isang hilera bawat kausap
@router.get("", response_model=list[ConversationResponse])
async def view_conversations(
    current_user: User = Depends(get_current_user),
    service: MessageService = Depends(get_message_service),
):
    return await service.get_conversations(current_user.id)


# Real-time: nasa routers/websocket_router.py (ws://.../ws). Dito, pagkatapos ng POST, itinutulak ang event sa kausap


# Loob ng usapan: pinakabagong `limit`; para sa mas luma, ipasa ang id ng pinakamatanda mong hawak bilang before_id
@router.get("/{other_user_id}", response_model=list[MessageResponse])
async def view_messages(
    other_user_id: int = Path(gt=0),
    limit: int = Query(50, ge=1, le=100),
    before_id: int | None = Query(None, gt=0),
    current_user: User = Depends(get_current_user),
    service: MessageService = Depends(get_message_service),
):
    return await service.get_messages(current_user.id, other_user_id, limit, before_id)


@router.post("/{other_user_id}", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    data: MessageCreate,
    background_tasks: BackgroundTasks,
    other_user_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: MessageService = Depends(get_message_service),
):
    message = await service.send_message(current_user.id, other_user_id, data)
    payload = {"type": "message", "data": MessageResponse.model_validate(message).model_dump(mode="json")}
    background_tasks.add_task(manager.send_to_user, other_user_id, payload)  # pagkatapos ng response; hindi hawak ang DB
    return message


# I-edit ang sarili mong text na mensahe. Susundan ng event na "message_edited" sa kausap
@router.patch("/{other_user_id}/{message_id}", response_model=MessageResponse)
async def edit_message(
    data: MessageUpdate,
    background_tasks: BackgroundTasks,
    other_user_id: int = Path(gt=0),
    message_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: MessageService = Depends(get_message_service),
):
    message = await service.edit_message(current_user.id, other_user_id, message_id, data)
    payload = {"type": "message_edited", "data": MessageResponse.model_validate(message).model_dump(mode="json")}
    background_tasks.add_task(manager.send_to_user, other_user_id, payload)
    return message


# Burahin ang sarili mong mensahe (soft delete). Susundan ng event na "message_deleted" sa kausap
@router.delete("/{other_user_id}/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    background_tasks: BackgroundTasks,
    other_user_id: int = Path(gt=0),
    message_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: MessageService = Depends(get_message_service),
):
    await service.delete_message(current_user.id, other_user_id, message_id)
    background_tasks.add_task(
        manager.send_to_user, other_user_id, {"type": "message_deleted", "data": {"id": message_id}}
    )


# Binuksan ang usapan: markahang nabasa, at sabihan ang nagpadala
@router.post("/{other_user_id}/read", response_model=MarkReadResponse)
async def mark_read(
    background_tasks: BackgroundTasks,
    other_user_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: MessageService = Depends(get_message_service),
):
    marked = await service.mark_read(current_user.id, other_user_id)
    if marked:
        background_tasks.add_task(
            manager.send_to_user, other_user_id, {"type": "read", "data": {"reader_id": current_user.id}}
        )
    return MarkReadResponse(marked_read=marked)
