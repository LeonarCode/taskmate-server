from fastapi import APIRouter, BackgroundTasks, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from utils.auth_dependency import get_current_user
from utils.realtime import push_notifications
from models import User
from schemas.group_task_schema import GroupTaskCreate, GroupTaskUpdate, GroupTaskResponse
from services.group_task_service import GroupTaskService

# May {server_id} ang lahat ng route (walang bare na "" sa prefix), para hindi sumagi sa "/server/{server_id}"
router = APIRouter(prefix="/server/task", tags=["group-task"])


def get_group_task_service(db: AsyncSession = Depends(get_db)) -> GroupTaskService:
    return GroupTaskService(db)


# Owner: lahat. Member: makita at mag-mark as completed lang.
# Hindi kasali sa server: 404. Member na hindi puwede sa ginagawa: 403.

# Server tab, Tasks: lahat ng task ng server, pinakamaaga ang deadline muna
@router.get("/{server_id}", response_model=list[GroupTaskResponse])
async def view_group_tasks(
    server_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: GroupTaskService = Depends(get_group_task_service),
):
    return await service.view_group_tasks(current_user.id, server_id)


# Owner lang
@router.post("/{server_id}", response_model=GroupTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_group_task(
    data: GroupTaskCreate,
    background_tasks: BackgroundTasks,
    server_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: GroupTaskService = Depends(get_group_task_service),
):
    task = await service.create_group_task(current_user.id, server_id, data)
    push_notifications(background_tasks, service.drain_notifications())  # sa mga member: "May bagong task"
    return task


# Owner lang. Ang ipinadala lang ang nababago
@router.patch("/{server_id}/{task_id}", response_model=GroupTaskResponse)
async def update_group_task(
    data: GroupTaskUpdate,
    server_id: int = Path(gt=0),
    task_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: GroupTaskService = Depends(get_group_task_service),
):
    return await service.update_group_task(current_user.id, server_id, task_id, data)


# Ang checkbox: kahit sinong member ang makakapag-mark as completed
@router.post("/{server_id}/{task_id}/complete", response_model=GroupTaskResponse)
async def complete_group_task(
    background_tasks: BackgroundTasks,
    server_id: int = Path(gt=0),
    task_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: GroupTaskService = Depends(get_group_task_service),
):
    task = await service.mark_task_complete(current_user.id, server_id, task_id)
    push_notifications(background_tasks, service.drain_notifications())  # sa may-ari, kapag member ang nag-complete
    return task


# I-undo ang complete: owner lang
@router.post("/{server_id}/{task_id}/incomplete", response_model=GroupTaskResponse)
async def incomplete_group_task(
    server_id: int = Path(gt=0),
    task_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: GroupTaskService = Depends(get_group_task_service),
):
    return await service.mark_task_incomplete(current_user.id, server_id, task_id)


# Owner lang (soft delete)
@router.delete("/{server_id}/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group_task(
    server_id: int = Path(gt=0),
    task_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: GroupTaskService = Depends(get_group_task_service),
):
    await service.delete_group_task(current_user.id, server_id, task_id)
