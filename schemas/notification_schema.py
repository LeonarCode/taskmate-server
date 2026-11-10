from datetime import datetime
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from utils.enum import NotifType


class ReferenceResponse(BaseModel):
    # ang tinutukoy ng notification; isa lang ang may laman. Gamitin sa pag-navigate ayon sa notification_type
    model_config = ConfigDict(from_attributes=True)

    task_id: int | None = None
    server_id: int | None = None
    dm_id: int | None = None  # id ng mensahe (hindi ng kausap)


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    notification_type: NotifType
    is_read: bool
    created_at: datetime
    # notification_reference ang pangalan sa model; reference ang lalabas sa API.
    # I-load ang notification_reference (selectinload) bago i-validate
    reference: ReferenceResponse | None = Field(
        default=None, validation_alias=AliasChoices("notification_reference", "reference")
    )


class UnreadCountResponse(BaseModel):
    # para sa badge ng Alerts tab
    unread_count: int
