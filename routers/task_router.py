from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from utils.auth_dependency import get_current_user
from models import Task, User
from schemas.task_schema import TaskCreate, TaskResponse, TaskUpsert
from services.task_service import TaskService

router = APIRouter(prefix="/task", tags=["tasks"])

def get_task_service(db: AsyncSession = Depends(get_db)) -> TaskService:
    return TaskService(db)

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    return await service.task_create(current_user.id, data)

@router.get("", response_model=list[TaskResponse])
async def view_tasks(
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    return await service.task_view(current_user.id)

# Sync ng app: ang UUID na ginawa ng app ang ID ng task. Ligtas ulitin: pareho ang resulta (gumawa o i-update).
# Kasama na rito ang checkbox: ipadala ang buong task na may is_complete (at completed_at)
@router.put("/{client_id}", response_model=TaskResponse)
async def upsert_task(
    data: TaskUpsert,
    client_id: UUID,
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    return await service.task_upsert(current_user.id, client_id, data)

# Ligtas ding ulitin: 204 kahit wala o nabura na ang task
@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    client_id: UUID,
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    await service.task_delete_by_client_id(current_user.id, client_id)
