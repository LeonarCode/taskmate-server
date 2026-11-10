from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator
from schemas.user_schema import UserPublic
from utils.enum import MessageType

class MessageBase(BaseModel):
    content: str = ""
    task_ref_id: int | None = None
    image_url: str | None = None
    message_type: MessageType = MessageType.TEXT

class MessageCreate(MessageBase):
    # limit at patakaran sa pagpapadala lang, hindi sa response, para mababasa pa rin ang mga lumang mensahe
    content: str = Field(default="", max_length=4000)
    task_ref_id: int | None = Field(default=None, gt=0)
    image_url: str | None = Field(default=None, max_length=2048, pattern=r"^https?://\S+$")

    @model_validator(mode="after")
    def check_by_type(self):
        if self.message_type == MessageType.SYSTEM_MESSAGE:
            raise ValueError("system_message cannot be sent by clients")
        if self.message_type == MessageType.TEXT and not self.content.strip():
            raise ValueError("content is required for text messages")
        if self.message_type == MessageType.IMAGE and not self.image_url:
            raise ValueError("image_url is required for image messages")
        if self.message_type == MessageType.TASK_REF and self.task_ref_id is None:
            raise ValueError("task_ref_id is required for task_ref messages")
        return self

class MessageUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def not_blank(self):
        if not self.content.strip():
            raise ValueError("content cannot be blank")
        return self

class MessageResponse(MessageBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_id: int
    receiver_id: int
    is_read: bool
    edited_at: datetime | None = None  # may laman kung na-edit; ipakita ang "(edited)"
    created_at: datetime

class MarkReadResponse(BaseModel):
    marked_read: int

class ConversationResponse(BaseModel):
    # isang hilera sa Chats tab
    partner: UserPublic
    last_message: MessageResponse
    unread_count: int

