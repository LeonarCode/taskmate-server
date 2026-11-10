from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from utils.auth_dependency import get_current_user
from utils.realtime import push_notifications
from models import User
from schemas.server_schema import ServerCreate, ServerUpdate, ServerResponse, MemberResponse
from services.server_service import ServerService

router = APIRouter(prefix="/server", tags=["server"])


def get_server_service(db: AsyncSession = Depends(get_db)) -> ServerService:
    return ServerService(db)


# Servers screen, "Joined": mga server na kasali ako (kasama ang sarili kong server)
@router.get("", response_model=list[ServerResponse])
async def my_servers(
    current_user: User = Depends(get_current_user),
    service: ServerService = Depends(get_server_service),
):
    return await service.get_joined_servers(current_user.id)


# Servers screen, "Discover": mga server na hindi pa ako kasali, pinakamaraming member muna.
# Dapat nasa itaas ito ng "/{server_id}": kung hindi, ang "discover" ay ituturing na server_id (422)
@router.get("/discover", response_model=list[ServerResponse])
async def discover_servers(
    search: str | None = Query(None, max_length=255),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    service: ServerService = Depends(get_server_service),
):
    return await service.get_other_servers(current_user.id, search, limit, offset)


# Create Server sheet
@router.post("", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
async def create_server(
    data: ServerCreate,
    current_user: User = Depends(get_current_user),
    service: ServerService = Depends(get_server_service),
):
    return await service.create_server(current_user.id, data)


# Detail ng server: 404 kung hindi ka owner o member
@router.get("/{server_id}", response_model=ServerResponse)
async def view_server(
    server_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: ServerService = Depends(get_server_service),
):
    return await service.get_server(current_user.id, server_id)


# Owner lang (member: 403). Ang ipinadala lang ang nababago
@router.patch("/{server_id}", response_model=ServerResponse)
async def update_server(
    data: ServerUpdate,
    server_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: ServerService = Depends(get_server_service),
):
    return await service.update_server(current_user.id, server_id, data)


# Owner lang (member: 403). Hindi na mababawi: nabubura rin ang members, tasks, mensahe at ratings
@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    background_tasks: BackgroundTasks,
    server_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: ServerService = Depends(get_server_service),
):
    await service.delete_server(current_user.id, server_id)
    push_notifications(background_tasks, service.drain_notifications())  # sa mga member: "Nabura ang server"


# Join: ligtas ulitin (hindi nadadagdagan ang member_count). Ibinabalik ang server para mabuksan agad
@router.post("/{server_id}/join", response_model=ServerResponse)
async def join_server(
    background_tasks: BackgroundTasks,
    server_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: ServerService = Depends(get_server_service),
):
    await service.join_server(current_user.id, server_id)
    push_notifications(background_tasks, service.drain_notifications())  # sa may-ari: "May sumali" (unang join lang)
    return await service.get_server(current_user.id, server_id)


# Leave: member lang. Ang owner ay 400, burahin na lang ang server
@router.post("/{server_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_server(
    background_tasks: BackgroundTasks,
    server_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: ServerService = Depends(get_server_service),
):
    await service.leave_server(current_user.id, server_id)
    push_notifications(background_tasks, service.drain_notifications())  # sa may-ari: "May umalis"


# Members tab: ang may-ari muna
@router.get("/{server_id}/members", response_model=list[MemberResponse])
async def view_members(
    server_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: ServerService = Depends(get_server_service),
):
    return await service.get_members(current_user.id, server_id)
