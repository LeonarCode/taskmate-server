from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, Numeric, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SQLEnum
from config.database import Base
from utils.enum import UserType

if TYPE_CHECKING:
    from models.task import Task
    from models.server import Server, Member
    from models.rating import Rating
    from models.message import Message, GroupMessage
    from models.notification import Notification

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password: Mapped[str | None] = mapped_column(Text)  # None kung Google-only
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    fullname: Mapped[str] = mapped_column(String(255))
    username: Mapped[str] = mapped_column(String(255), unique=True)
    age: Mapped[int] = mapped_column(Integer)
    user_type: Mapped[UserType] = mapped_column(SQLEnum(UserType))
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    fcm_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    average_rating: Mapped[float] = mapped_column(Numeric(3, 2, asdecimal=False), default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tasks: Mapped[list[Task]] = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    owned_servers: Mapped[list[Server]] = relationship("Server", back_populates="owner", cascade="all, delete-orphan")
    memberships: Mapped[list[Member]] = relationship("Member", back_populates="user", cascade="all, delete-orphan")
    ratings_given: Mapped[list[Rating]] = relationship("Rating", foreign_keys="[Rating.rater_id]", back_populates="rater", cascade="all, delete-orphan")
    ratings_received: Mapped[list[Rating]] = relationship("Rating", foreign_keys="[Rating.rated_id]", back_populates="rated", cascade="all, delete-orphan")
    messages_sent: Mapped[list[Message]] = relationship("Message", foreign_keys="[Message.sender_id]", back_populates="sender", cascade="all, delete-orphan")
    messages_received: Mapped[list[Message]] = relationship("Message", foreign_keys="[Message.receiver_id]", back_populates="receiver", cascade="all, delete-orphan")
    group_messages_sent: Mapped[list[GroupMessage]] = relationship("GroupMessage", foreign_keys="[GroupMessage.sender_id]", back_populates="sender", cascade="all, delete-orphan")
    notifications: Mapped[list[Notification]] = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

    @property
    def has_photo(self) -> bool:
        return bool(self.photo_url)



