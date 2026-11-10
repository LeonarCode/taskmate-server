from datetime import datetime
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator
from schemas.user_schema import UserPublic
from utils.enum import MessageType

class GroupMessageBase(BaseModel):
    content: str = ""
    task_ref_id: int | None = None
    image_url: str | None = None
    message_type: MessageType = MessageType.TEXT

class GroupMessageCreate(GroupMessageBase):
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

class GroupMessageUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def not_blank(self):
        if not self.content.strip():
            raise ValueError("content cannot be blank")
        return self

class GroupMessageResponse(GroupMessageBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_id: int
    # pangalan at larawan ng nagpadala (has_photo): i-load ang sender gamit ang selectinload(GroupMessage.sender)
    sender: UserPublic
    # group_id ang pangalan ng column sa model; server_id ang lalabas sa API, tulad ng sa GroupTask
    server_id: int = Field(validation_alias=AliasChoices("group_id", "server_id"))
    edited_at: datetime | None = None  # may laman kung na-edit; ipakita ang "(edited)"
    created_at: datetime
