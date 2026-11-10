from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from models import Server, Member
from repositories.rating_repository import RatingRepository
from repositories.server_repository import ServerRepository
from repositories.user_repository import UserRepository
from schemas.server_schema import ServerCreate, ServerUpdate, MemberResponse
from schemas.user_schema import UserPublic
from services.notification_service import NotificationService
from utils.enum import NotifType
from utils.exceptions import BadRequestError, ForbiddenError, NotFoundError

MAX_PAGE_SIZE = 100

class ServerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ServerRepository(db)
        self.users = UserRepository(db)
        self.ratings = RatingRepository(db)
        self.notifications = NotificationService(db)

    def drain_notifications(self):
        """Mga nagawang notification ng request na ito, para itulak ng router sa socket (utils/realtime.push_notifications)."""
        return self.notifications.drain()

    async def _display_name(self, user_id: int) -> str:
        user = await self.users.find_user_by_id(user_id)
        return (user.fullname or user.username) if user else "Someone"

    async def _get_for_member(self, user_id: int, server_id: int) -> Server:
        # None kung hindi owner o member: 404 din, para hindi malaman na may ganoong server
        server = await self.repo.get_server(server_id, user_id)
        if server is None:
            raise NotFoundError("Server not found")
        return server

    async def _get_for_owner(self, user_id: int, server_id: int) -> Server:
        server = await self._get_for_member(user_id, server_id)
        if server.owner_id != user_id:  # member lang siya
            raise ForbiddenError("Only the server owner can do this")
        return server

    async def create_server(self, user_id: int, data: ServerCreate) -> Server:
        return await self.repo.create_server(
            name = data.name,
            description = data.description,
            owner_id = user_id,
            icon_color = data.icon_color,
            icon_emoji = data.icon_emoji
        )

    async def get_joined_servers(self, user_id: int) -> list[Server]:
        return await self.repo.get_joined_servers(user_id)

    async def get_other_servers(
        self, user_id: int, search: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[Server]:
        limit = max(1, min(limit, MAX_PAGE_SIZE))
        return await self.repo.get_other_servers(user_id, search.strip() if search else None, limit, max(0, offset))

    async def get_server(self, user_id: int, server_id: int) -> Server:
        return await self._get_for_member(user_id, server_id)

    async def get_members(self, user_id: int, server_id: int) -> list[MemberResponse]:
        server = await self._get_for_member(user_id, server_id)
        members = await self.repo.get_server_members(server_id)
        users = {u.id: u for u in await self.users.find_users_by_ids([m.user_id for m in members])}  # isang query
        return [
            MemberResponse(
                user=UserPublic.model_validate(users[m.user_id]),
                joined_at=m.joined_at,
                is_owner=m.user_id == server.owner_id,
            )
            for m in members
        ]

    async def join_server(self, user_id: int, server_id: int) -> Member:
        server = await self.repo.find_server(server_id)
        if server is None:
            raise NotFoundError("Server not found")
        member = await self.repo.get_member(server_id, user_id)
        if member is not None:  # nasa server na (kasama ang may-ari): huwag nang dagdagan ang member_count
            return member
        try:
            member = await self.repo.join_server(
                server_id = server_id,
                user_id = user_id
            )
        except IntegrityError:  # naunahan ng parehong request (hal. dalawang beses na-tap ang Join)
            await self.db.rollback()
            member = await self.repo.get_member(server_id, user_id)
            if member is None:
                raise
            return member  # ang naunang request ang nag-abiso na sa may-ari
        # abisuhan ang may-ari; kung mabigo ito, nakasali pa rin ang user
        await self.notifications.notify_many_safely(
            [server.owner_id],
            f"{await self._display_name(user_id)} joined {server.name}",
            NotifType.SERVER_ACTIVITY,
            server_id = server_id,
        )
        return member

    async def leave_server(self, user_id: int, server_id: int) -> None:
        server = await self._get_for_member(user_id, server_id)
        if server.owner_id == user_id:
            raise BadRequestError("The owner cannot leave. Delete the server instead.")
        if not await self.repo.remove_member(user_id, server_id):
            return  # wala nang ibubura (naunahan ng parehong request): walang aabisuhan
        await self.notifications.notify_many_safely(
            [server.owner_id],
            f"{await self._display_name(user_id)} left {server.name}",
            NotifType.SERVER_ACTIVITY,
            server_id = server_id,
        )

    async def update_server(self, user_id: int, server_id: int, data: ServerUpdate) -> Server:
        server = await self._get_for_owner(user_id, server_id)
        return await self.repo.update_server(server, **data.model_dump(exclude_unset=True))

    async def delete_server(self, user_id: int, server_id: int) -> None:
        server = await self._get_for_owner(user_id, server_id)
        name = server.name
        member_ids = [m.user_id for m in await self.repo.get_server_members(server_id) if m.user_id != user_id]
        rated_ids = await self.ratings.get_rated_user_ids(server_id)
        await self.repo.delete_server(server_id)
        await self.ratings.refresh_summaries(rated_ids)  # nabura rin ang mga rating sa server na ito (cascade)
        # walang server_id na ituturo: nabura na ang server, at kasama nitong mabubura ang notification na may reference dito
        await self.notifications.notify_many_safely(
            member_ids, f"{name} was deleted by its owner", NotifType.SERVER_ACTIVITY
        )
