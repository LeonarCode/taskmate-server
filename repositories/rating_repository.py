from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from models import Rating, User


class RatingRepository:
    """Walang pagsusuri ng membership dito; ang service ang titingin muna. Ang rater_id o rated_id ay laging bahagi ng hanap,
    kaya hindi makukuha o magagalaw ang rating ng iba.

    Ang users.average_rating at users.rating_count ay kinukuwenta rito sa tuwing may nagbago, sa iisang transaction ng pagbabago."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _query():
        # kasama na ang rater, rated at server para magamit agad sa RatingResponse (kung hindi, MissingGreenlet)
        return select(Rating).options(
            selectinload(Rating.rater), selectinload(Rating.rated), selectinload(Rating.server)
        )

    async def _lock_users(self, user_ids: list[int]) -> None:
        # Sunod-sunod ang sabay na pag-rate sa iisang user (PostgreSQL), kaya hindi nagpapalitan ng lumang average.
        # Nakaayos ang id para walang deadlock kapag marami. Walang epekto sa SQLite.
        await self.db.execute(select(User.id).where(User.id.in_(user_ids)).order_by(User.id).with_for_update())

    async def _recalculate(self, user_ids: list[int]) -> None:
        # walang commit dito: kasama ng pagbabago ng rating
        rows = await self.db.execute(
            select(Rating.rated_id, func.avg(Rating.score), func.count())
            .where(Rating.rated_id.in_(user_ids))
            .group_by(Rating.rated_id)
        )
        stats = {user_id: (average, count) for user_id, average, count in rows.all()}
        await self.db.execute(
            update(User),  # bulk update ayon sa primary key; 0 at 0 ang walang natirang rating
            [
                {
                    "id": user_id,
                    "average_rating": round(float(stats[user_id][0]), 2) if user_id in stats else 0.0,
                    "rating_count": stats[user_id][1] if user_id in stats else 0,
                }
                for user_id in user_ids
            ],
        )

    async def refresh_summaries(self, user_ids: list[int]) -> None:
        """Kuwentahin ulit ang average at bilang ng mga user. Para sa pagkabura ng server, na nagbubura ng mga rating
        nang hindi dumadaan dito (ON DELETE CASCADE)."""
        user_ids = sorted(set(user_ids))
        if not user_ids:
            return
        await self._lock_users(user_ids)
        await self._recalculate(user_ids)
        await self.db.commit()

    async def get_rating(self, rater_id: int, rated_id: int, server_id: int) -> Rating | None:
        return await self.db.scalar(
            self._query().where(
                Rating.rater_id == rater_id, Rating.rated_id == rated_id, Rating.server_id == server_id
            )
        )

    async def save_rating(
        self, rater_id: int, rated_id: int, server_id: int, score: float, comment: str | None
    ) -> Rating:
        """Gagawa ng bago, o papalitan ang dati (isa lang bawat rater, rated at server)."""
        await self._lock_users([rated_id])
        rating = await self.db.scalar(
            select(Rating).where(
                Rating.rater_id == rater_id, Rating.rated_id == rated_id, Rating.server_id == server_id
            )
        )
        if rating is None:
            rating = Rating(rater_id=rater_id, rated_id=rated_id, server_id=server_id, score=score, comment=comment)
            self.db.add(rating)
        else:
            rating.score = score
            rating.comment = comment
        await self.db.flush()
        await self._recalculate([rated_id])
        await self.db.commit()
        # i-load ulit (kasama ang created_at at ang bagong average ng rated) sa isang query
        return await self.db.scalar(
            self._query().where(Rating.id == rating.id).execution_options(populate_existing=True)
        )

    async def delete_rating(self, rater_id: int, rated_id: int, server_id: int) -> bool:
        rating_id = await self.db.scalar(
            select(Rating.id).where(
                Rating.rater_id == rater_id, Rating.rated_id == rated_id, Rating.server_id == server_id
            )
        )
        if rating_id is None:
            return False
        await self._lock_users([rated_id])
        await self.db.execute(delete(Rating).where(Rating.id == rating_id))
        await self._recalculate([rated_id])
        await self.db.commit()
        return True

    async def get_given(
        self, rater_id: int, server_id: int | None = None, limit: int = 50, before_id: int | None = None
    ) -> list[Rating]:
        # mga ni-rate ko, pinakabago muna
        query = self._query().where(Rating.rater_id == rater_id)
        if server_id is not None:
            query = query.where(Rating.server_id == server_id)
        if before_id is not None:
            query = query.where(Rating.id < before_id)
        result = await self.db.scalars(query.order_by(Rating.id.desc()).limit(limit))
        return list(result.all())

    async def get_received(self, rated_id: int, limit: int = 50, before_id: int | None = None) -> list[Rating]:
        # mga nag-rate sa akin, pinakabago muna
        query = self._query().where(Rating.rated_id == rated_id)
        if before_id is not None:
            query = query.where(Rating.id < before_id)
        result = await self.db.scalars(query.order_by(Rating.id.desc()).limit(limit))
        return list(result.all())

    async def get_rated_user_ids(self, server_id: int) -> list[int]:
        result = await self.db.scalars(select(Rating.rated_id).where(Rating.server_id == server_id).distinct())
        return list(result.all())
