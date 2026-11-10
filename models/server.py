from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, UniqueConstraint, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.database import Base
from utils.enum import Colors

if TYPE_CHECKING:
    from models.user import User
    from models.task import GroupTask
    from models.rating import Rating
    from models.message import GroupMessage
    from models.notification import Reference

class Member(Base):
    __tablename__ = "server_members"
    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    server: Mapped[Server] = relationship("Server", back_populates="members")
    user: Mapped[User] = relationship("User", back_populates="memberships")

    __table_args__ = (UniqueConstraint("server_id", "user_id", name="uq_member_server_user"),)

class Server(Base):
    __tablename__ = "servers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    icon_color: Mapped[Colors] = mapped_column(SQLEnum(Colors), default=Colors.PURPLE)
    icon_emoji: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    member_count: Mapped[int] = mapped_column(Integer, default=1)

    owner: Mapped[User] = relationship("User", back_populates="owned_servers")
    members: Mapped[list[Member]] = relationship("Member", back_populates="server", cascade="all, delete-orphan")
    group_tasks: Mapped[list[GroupTask]] = relationship("GroupTask", back_populates="server", cascade="all, delete-orphan")
    ratings: Mapped[list[Rating]] = relationship("Rating", back_populates="server", cascade="all, delete-orphan")
    group_messages: Mapped[list[GroupMessage]] = relationship("GroupMessage", back_populates="group", cascade="all, delete-orphan")
    references: Mapped[list[Reference]] = relationship("Reference", back_populates="from_server", cascade="all")


