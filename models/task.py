from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.database import Base
from utils.enum import TaskPriority

if TYPE_CHECKING:
    from models.user import User
    from models.server import Server
    from models.message import Message, GroupMessage
    from models.notification import Reference

class GroupTask(Base):
    __tablename__ = "group_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[TaskPriority] = mapped_column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM)
    has_alarm: Mapped[bool] = mapped_column(Boolean, default=True)
    is_synced: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    client_id: Mapped[str | None] = mapped_column(String(36), unique=True)  # UUID galing Flutter

    server: Mapped[Server] = relationship("Server", back_populates="group_tasks")
    group_messages: Mapped[list[GroupMessage]] = relationship("GroupMessage", back_populates="task_ref", cascade="all")

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    uid: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[TaskPriority] = mapped_column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM)
    has_alarm: Mapped[bool] = mapped_column(Boolean, default=True)
    is_synced: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    client_id: Mapped[str | None] = mapped_column(String(36))  # UUID galing Flutter; unique bawat user (tingnan sa baba)

    user: Mapped[User] = relationship("User", back_populates="tasks")
    messages: Mapped[list[Message]] = relationship("Message", back_populates="task_ref", cascade="save-update, merge", passive_deletes=True)
    references: Mapped[list[Reference]] = relationship("Reference", back_populates="from_task", cascade="all")
    __table_args__ = (UniqueConstraint("uid", "client_id", name="uq_tasks_uid_client_id"),)
