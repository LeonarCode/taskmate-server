from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Index, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.database import Base
from utils.enum import NotifType

if TYPE_CHECKING:
    from models.user import User
    from models.task import Task
    from models.server import Server
    from models.message import Message

class Reference(Base):
    __tablename__ = "notif_references"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    server_id: Mapped[int | None] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), nullable=True)
    dm_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), nullable=True)

    from_task: Mapped[Task] = relationship("Task", back_populates="references")
    from_server: Mapped[Server] = relationship("Server", back_populates="references")
    from_dm: Mapped[Message] = relationship("Message", back_populates="notif_references")
    notifications: Mapped[list[Notification]] = relationship("Notification", back_populates="notification_reference", cascade="all")



class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(String(255))
    notification_type: Mapped[NotifType] = mapped_column(SQLEnum(NotifType))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    reference_id: Mapped[int | None] = mapped_column(ForeignKey("notif_references.id", ondelete="CASCADE"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="notifications")
    notification_reference: Mapped[Reference] = relationship("Reference", back_populates="notifications")
    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "is_read"),
    )