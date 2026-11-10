from sqlalchemy.ext.asyncio import AsyncSession
from models import Rating
from repositories.rating_repository import RatingRepository
from repositories.server_repository import ServerRepository
from schemas.rating_schema import RatingUpsert
from utils.exceptions import BadRequestError, NotFoundError

MAX_PAGE_SIZE = 100

# Magkapwa member (kasama ang may-ari) ng iisang server ang puwedeng mag-rate, isang beses bawat tao bawat server.
# Ang pag-rate ulit ay pagpapalit ng dati. Hindi puwedeng i-rate ang sarili.
class RatingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RatingRepository(db)
        self.servers = ServerRepository(db)

    async def rate_user(self, rater_id: int, server_id: int, rated_id: int, data: RatingUpsert) -> Rating:
        # hindi kasali sa server: 404 din, para hindi malaman na may ganoong server
        server = await self.servers.get_server(server_id, rater_id)
        if server is None:
            raise NotFoundError("Server not found")
        if rated_id == rater_id:
            raise BadRequestError("You cannot rate yourself")
        if rated_id != server.owner_id and await self.servers.get_member(server_id, rated_id) is None:
            raise NotFoundError("Member not found")
        return await self.repo.save_rating(rater_id, rated_id, server_id, data.score, data.comment)

    async def remove_rating(self, rater_id: int, server_id: int, rated_id: int) -> None:
        # sarili mong rating, kaya hindi na tinitingnan kung kasali ka pa sa server
        if not await self.repo.delete_rating(rater_id, rated_id, server_id):
            raise NotFoundError("Rating not found")

    async def get_given(
        self, user_id: int, server_id: int | None = None, limit: int = 50, before_id: int | None = None
    ) -> list[Rating]:
        limit = max(1, min(limit, MAX_PAGE_SIZE))
        return await self.repo.get_given(user_id, server_id, limit, before_id)

    async def get_received(self, user_id: int, limit: int = 50, before_id: int | None = None) -> list[Rating]:
        limit = max(1, min(limit, MAX_PAGE_SIZE))
        return await self.repo.get_received(user_id, limit, before_id)
