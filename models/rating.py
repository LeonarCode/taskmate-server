from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey, DateTime, Numeric, UniqueConstraint, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.database import Base

if TYPE_CHECKING:
    from models.user import User
    from models.server import Server

class Rating(Base):
    __tablename__ = "ratings"
    id: Mapped[int] = mapped_column(primary_key=True)
    rater_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    rated_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), index=True)
    score: Mapped[float] = mapped_column(Numeric(3, 2, asdecimal=False))
    comment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    rater: Mapped[User] = relationship("User", foreign_keys="[Rating.rater_id]", back_populates="ratings_given")
    rated: Mapped[User] = relationship("User", foreign_keys="[Rating.rated_id]", back_populates="ratings_received")
    server: Mapped[Server] = relationship("Server", back_populates="ratings")
    __table_args__ = (
        UniqueConstraint("rater_id", "rated_id", "server_id", name="uq_rating_once_per_server"),
        CheckConstraint("score >= 1 AND score <= 5", name="ck_rating_score_range"),  # 1 hanggang 5 na bituin sa app
        CheckConstraint("rater_id <> rated_id", name="ck_rating_not_self"),
    )