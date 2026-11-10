from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from utils.auth_dependency import get_current_user
from utils.connection_manager import manager
from models import User
from schemas.group_message_schema import GroupMessageCreate, GroupMessageUpdate, GroupMessageResponse
from services.group_message_service import GroupMessageService

# May {server_id} ang lahat ng route (walang bare na "" sa prefix), para hindi sumagi sa "/server/{server_id}"
router = APIRouter(prefix="/server/messages", tags=["group-messages"])


def get_group_message_service(db: AsyncSession = Depends(get_db)) -> GroupMessageService:
    return GroupMessageService(db)


# Real-time: gamitin ang parehong WebSocket ng DM (routers/websocket_router.py, ws://.../ws). Sa REST pa rin nagpapadala ang app;
# pagkatapos, itinutulak ang event sa ibang member (hindi sa nagpadala). Nasa data ang server_id ng chat:
#   {"type": "group_message", "data": {...GroupMessageResponse}}
#   {"type": "group_message_edited", "data": {...GroupMessageResponse}}
#   {"type": "group_message_deleted", "data": {"id": ..., "server_id": ...}}


# Server chat: pinakabagong `limit`, mula luma pataas; para sa mas luma, ipasa ang id ng pinakamatanda mong hawak bilang before_id
@router.get("/{server_id}", response_model=list[GroupMessageResponse])
async def view_group_messages(
    server_id: int = Path(gt=0),
    limit: int = Query(50, ge=1, le=100),
    before_id: int | None = Query(None, gt=0),
    current_user: User = Depends(get_current_user),
    service: GroupMessageService = Depends(get_group_message_service),
):
    return await service.get_group_messages(current_user.id, server_id, limit, before_id)


# Member lang (kasama ang owner)
@router.post("/{server_id}", response_model=GroupMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_group_message(
    data: GroupMessageCreate,
    background_tasks: BackgroundTasks,
    server_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: GroupMessageService = Depends(get_group_message_service),
):
    message = await service.send_group_message(current_user.id, server_id, data)
    recipients = await service.get_recipient_ids(current_user.id, server_id)  # kunin habang bukas pa ang DB
    payload = {"type": "group_message", "data": GroupMessageResponse.model_validate(message).model_dump(mode="json")}
    background_tasks.add_task(manager.send_to_users, recipients, payload)  # pagkatapos ng response; hindi hawak ang DB
    return message


# I-edit ang sarili mong text na mensahe (kahit owner ka, hindi ang sa iba)
@router.patch("/{server_id}/{message_id}", response_model=GroupMessageResponse)
async def edit_group_message(
    data: GroupMessageUpdate,
    background_tasks: BackgroundTasks,
    server_id: int = Path(gt=0),
    message_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: GroupMessageService = Depends(get_group_message_service),
):
    message = await service.edit_group_message(current_user.id, server_id, message_id, data)
    recipients = await service.get_recipient_ids(current_user.id, server_id)
    payload = {"type": "group_message_edited", "data": GroupMessageResponse.model_validate(message).model_dump(mode="json")}
    background_tasks.add_task(manager.send_to_users, recipients, payload)
    return message


# Burahin ang sarili mong mensahe (soft delete)
@router.delete("/{server_id}/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group_message(
    background_tasks: BackgroundTasks,
    server_id: int = Path(gt=0),
    message_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: GroupMessageService = Depends(get_group_message_service),
):
    await service.delete_group_message(current_user.id, server_id, message_id)
    recipients = await service.get_recipient_ids(current_user.id, server_id)
    payload = {"type": "group_message_deleted", "data": {"id": message_id, "server_id": server_id}}
    background_tasks.add_task(manager.send_to_users, recipients, payload)
