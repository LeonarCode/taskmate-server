from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, Boolean, Index, ForeignKey, false, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.database import Base
from utils.enum import MessageType

if TYPE_CHECKING:
    from models.user import User
    from models.task import Task, GroupTask
    from models.server import Server
    from models.notification import Reference

class GroupMessage(Base):
    __tablename__ = "group_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text)
    task_ref_id: Mapped[int] = mapped_column(ForeignKey("group_tasks.id", ondelete="CASCADE"), nullable=True)
    image_url: Mapped[str] = mapped_column(Text, nullable=True)
    message_type: Mapped[MessageType] = mapped_column(SQLEnum(MessageType), default=MessageType.TEXT)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # nakalagay lang kapag na-edit
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())  # soft delete
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sender: Mapped[User] = relationship("User", back_populates="group_messages_sent")
    group: Mapped[Server] = relationship("Server", back_populates="group_messages")
    task_ref: Mapped[GroupTask] = relationship("GroupTask", back_populates="group_messages")
    __table_args__ = (
        Index("ix_group_messages_group_created", "group_id", "created_at"),
    )

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    task_ref_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"))
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_type: Mapped[MessageType] = mapped_column(SQLEnum(MessageType), default=MessageType.TEXT)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())  # server_default para sa mga dati nang row
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # nakalagay lang kapag na-edit
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())  # soft delete
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sender: Mapped[User] = relationship("User", foreign_keys=[sender_id], back_populates="messages_sent")
    receiver: Mapped[User] = relationship("User", foreign_keys=[receiver_id], back_populates="messages_received")
    task_ref: Mapped[Task] = relationship("Task", back_populates="messages")
    notif_references: Mapped[list[Reference]] = relationship("Reference", back_populates="from_dm", cascade="all")
    __table_args__ = (
        Index("ix_messages_conversation", "sender_id", "receiver_id", "created_at"),
    )