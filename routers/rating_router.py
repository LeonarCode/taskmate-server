from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from utils.auth_dependency import get_current_user
from models import User
from schemas.rating_schema import RatingResponse, RatingUpsert
from services.rating_service import RatingService

router = APIRouter(prefix="/ratings", tags=["ratings"])


def get_rating_service(db: AsyncSession = Depends(get_db)) -> RatingService:
    return RatingService(db)


# Ang average at bilang ng rating ng bawat user ay nasa average_rating at rating_count ng user (Members tab, profile).
# Dito ang mga indibidwal na rating, na ikaw lang ang makakakita ng sa iyo.

# Mga ni-rate ko. Sa Members tab: ipasa ang server_id para makuha ang bituin na ibinigay ko sa bawat member
@router.get("/given", response_model=list[RatingResponse])
async def given_ratings(
    server_id: int | None = Query(None, gt=0),
    limit: int = Query(50, ge=1, le=100),
    before_id: int | None = Query(None, gt=0),
    current_user: User = Depends(get_current_user),
    service: RatingService = Depends(get_rating_service),
):
    return await service.get_given(current_user.id, server_id, limit, before_id)


# Mga nag-rate sa akin (may comment), pinakabago muna. Para sa mas luma, ipasa ang id ng pinakamatanda mong hawak bilang before_id
@router.get("/received", response_model=list[RatingResponse])
async def received_ratings(
    limit: int = Query(50, ge=1, le=100),
    before_id: int | None = Query(None, gt=0),
    current_user: User = Depends(get_current_user),
    service: RatingService = Depends(get_rating_service),
):
    return await service.get_received(current_user.id, limit, before_id)


# Mag-rate (1 hanggang 5, may kalahati). Ligtas ulitin: kung nai-rate mo na siya sa server na ito, napapalitan ang dati.
# Dapat magkapwa kayong member ng server. Sarili: 400. Hindi kasali sa server: 404
@router.put("/{server_id}/{rated_id}", response_model=RatingResponse)
async def rate_user(
    data: RatingUpsert,
    server_id: int = Path(gt=0),
    rated_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: RatingService = Depends(get_rating_service),
):
    return await service.rate_user(current_user.id, server_id, rated_id, data)


# Bawiin ang rating ko sa user na iyon sa server na iyon. 404 kung wala
@router.delete("/{server_id}/{rated_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_rating(
    server_id: int = Path(gt=0),
    rated_id: int = Path(gt=0),
    current_user: User = Depends(get_current_user),
    service: RatingService = Depends(get_rating_service),
):
    await service.remove_rating(current_user.id, server_id, rated_id)
