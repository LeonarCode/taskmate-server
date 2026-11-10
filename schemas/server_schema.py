from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator
from schemas.user_schema import UserPublic
from utils.enum import Colors

class ServerBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    icon_color: Colors = Colors.PURPLE
    icon_emoji: str | None = Field(default=None, max_length=16)


class ServerCreate(ServerBase):
    pass

class ServerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    icon_color: Colors | None = None
    icon_emoji: str | None = Field(default=None, max_length=16)

    @model_validator(mode="after")
    def no_explicit_null(self):
        # NOT NULL ang name, description at icon_color: ang hindi ipinadala ay hindi babaguhin, pero hindi puwede ang `null`.
        # Ang icon_emoji lang ang puwedeng alisin (null)
        nulls = sorted(f for f in self.model_fields_set if f != "icon_emoji" and getattr(self, f) is None)
        if nulls:
            raise ValueError(f"{', '.join(nulls)} cannot be null")
        return self

class ServerResponse(ServerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    member_count: int
    created_at: datetime

class MemberResponse(BaseModel):
    # isang hilera sa Members tab ng server
    user: UserPublic
    joined_at: datetime
    is_owner: bool

