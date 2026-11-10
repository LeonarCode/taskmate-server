from datetime import datetime
from typing import Annotated
from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, model_validator
from utils.enum import UserType


def _fits_bcrypt(value: str) -> str:
    # bcrypt 5.x: ValueError kapag lampas 72 *bytes* (hindi chars) ang password
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 bytes")
    return value

Password = Annotated[str, Field(min_length=8, max_length=72), AfterValidator(_fits_bcrypt)]

def _blank_to_none(value):
    # optional na field sa Flutter: kapag walang laman, "" ang ipinapadala, kaya gawing None
    if isinstance(value, str):
        return value.strip() or None
    return value

Organization = Annotated[Annotated[str, Field(max_length=255)] | None, BeforeValidator(_blank_to_none)]

def _normalize_username(value):
    # naka-lowercase ang username sa app (at sa pag-check ng availability), kaya ganoon din dito
    return value.strip().lower() if isinstance(value, str) else value

# sa pagpasok lang (create/update); hindi sa response, para hindi mabago ang nababasa mula sa database
Username = Annotated[str, BeforeValidator(_normalize_username), Field(min_length=1, max_length=255)]


class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    email: EmailStr
    fullname: str = Field(min_length=1, max_length=255)
    age: int = Field(ge=1, le=120)
    organization: Organization = None

class UserCreate(UserBase):
    username: Username
    password: Password
    user_type: UserType

class UserUpdate(BaseModel):
    username: Username | None = None
    email: EmailStr | None = None
    password: Password | None = None

def _strip(value):
    return value.strip() if isinstance(value, str) else value

class ProfileUpdate(BaseModel):
    # PATCH /users/me: ang Edit Profile sheet (full name, age, user type) at organization.
    # Ang hindi ipinadala ay hindi babaguhin; ang organization lang ang puwedeng alisin (null o blangko)
    fullname: Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=255)] | None = None
    age: int | None = Field(default=None, ge=1, le=120)
    user_type: UserType | None = None
    organization: Organization = None

    @model_validator(mode="after")
    def no_explicit_null(self):
        # NOT NULL ang fullname, age at user_type: hindi puwede ang `null`
        nulls = sorted(f for f in self.model_fields_set if f != "organization" and getattr(self, f) is None)
        if nulls:
            raise ValueError(f"{', '.join(nulls)} cannot be null")
        return self

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_type: UserType
    photo_url: str | None = None  # https URL (Cloudinary, Google) o data URL; sa sarili lang ito, hindi sa mga listahan
    average_rating: float = 0.0  # 0 kapag rating_count ay 0 (wala pang nag-rate)
    rating_count: int = 0
    created_at: datetime

class UserPublic(BaseModel):
    # para sa ibang user (chat, members): walang email, age at iba pang pribado
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    fullname: str
    # walang photo_url sa listahan: puwedeng data URL na hanggang ~800 KB (kapag walang Cloudinary). Kung True, kunin sa GET /users/{id}/photo
    has_photo: bool = False
    average_rating: float = 0.0  # 0 kapag rating_count ay 0 (wala pang nag-rate)
    rating_count: int = 0

class UserLogin(BaseModel):
    email: EmailStr
    # walang min 8 sa login (signup policy lang), pero checkpw nagra-raise din kapag >72 bytes
    password: Annotated[str, Field(min_length=1, max_length=72), AfterValidator(_fits_bcrypt)]

class GoogleLogin(BaseModel):
    id_token: str

class GoogleRegister(GoogleLogin):
    # email at photo_url ay kukunin sa verified token
    fullname: str = Field(min_length=1, max_length=255)
    username: Username
    age: int = Field(ge=1, le=120)
    user_type: UserType
    organization: Organization = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class Availability(BaseModel):
    available: bool

class ForgotPassword(BaseModel):
    email: EmailStr

class ResetPassword(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$")
    new_password: Password

class OkResponse(BaseModel):
    message: str

