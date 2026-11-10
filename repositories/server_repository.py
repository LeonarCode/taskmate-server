from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.server import Server, Member

class ServerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _member_server_ids(user_id: int):
        return select(Member.server_id).where(Member.user_id == user_id)

    async def create_server(self, **data) -> Server:
        server = Server(**data)
        server.members.append(Member(user_id=server.owner_id))  # kasama ang may-ari sa listahan ng members
        self.db.add(server)
        await self.db.commit()
        await self.db.refresh(server)
        return server

    async def find_server(self, server_id: int) -> Server | None:
        return await self.db.get(Server, server_id)

    async def get_member(self, server_id: int, user_id: int) -> Member | None:
        return await self.db.scalar(
            select(Member).where(Member.server_id == server_id, Member.user_id == user_id)
        )

    async def join_server(self, user_id: int, server_id: int) -> Member:
        member = Member(user_id=user_id, server_id=server_id)
        self.db.add(member)
        # isang transaction: kung duplicate (IntegrityError), hindi rin madadagdagan ang member_count
        await self.db.execute(
            update(Server).where(Server.id == server_id).values(member_count=Server.member_count + 1)
        )
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def remove_member(self, user_id: int, server_id: int) -> bool:
        result = await self.db.execute(
            delete(Member).where(Member.server_id == server_id, Member.user_id == user_id)
        )
        if result.rowcount:
            await self.db.execute(
                update(Server).where(Server.id == server_id).values(member_count=Server.member_count - 1)
            )
        await self.db.commit()
        return bool(result.rowcount)

    async def update_server(self, server: Server, **fields) -> Server:
        for name, value in fields.items():
            setattr(server, name, value)
        await self.db.commit()
        await self.db.refresh(server)
        return server

    async def delete_server(self, server_id: int) -> None:
        # bulk delete: ang database na ang magbubura ng members, tasks, mensahe at ratings (ON DELETE CASCADE),
        # hindi na ilo-load sa memory ang libu-libong mensahe
        await self.db.execute(delete(Server).where(Server.id == server_id))
        await self.db.commit()

    async def get_joined_servers(self, user_id: int) -> list[Server]:
        result = await self.db.scalars(
            select(Server)
            .where(or_(Server.owner_id == user_id, Server.id.in_(self._member_server_ids(user_id))))
            .order_by(Server.member_count)
        )
        return list(result.all())

    async def get_other_servers(
        self, user_id: int, search: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[Server]:
        query = select(Server).where(
            and_(Server.owner_id != user_id, Server.id.not_in(self._member_server_ids(user_id)))
        )
        if search:
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")  # literal ang % at _
            query = query.where(Server.name.ilike(f"%{escaped}%", escape="\\"))
        # pinakamaraming member muna
        result = await self.db.scalars(
            query.order_by(Server.member_count.desc(), Server.id).limit(limit).offset(offset)
        )
        return list(result.all())

    async def get_server(self, server_id: int, user_id: int) -> Server | None:
        return await self.db.scalar(
            select(Server).where(
                Server.id == server_id,
                or_(Server.owner_id == user_id, Server.id.in_(self._member_server_ids(user_id))),
            )
        )

    async def get_server_members(self, server_id: int) -> list[Member]:
        result = await self.db.scalars(
            select(Member).where(Member.server_id == server_id).order_by(Member.joined_at, Member.id)
        )
        return list(result.all())

