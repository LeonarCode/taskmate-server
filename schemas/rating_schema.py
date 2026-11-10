from datetime import datetime
from typing import Annotated
from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field
from schemas.user_schema import UserPublic


def _half_steps(value: float) -> float:
    # bituin sa app: 1, 1.5, 2 ... 5. Ang 4.3 ay hindi bituin
    if value * 2 != int(value * 2):
        raise ValueError("Score must be in steps of 0.5")
    return value

Score = Annotated[float, Field(strict=True, ge=1, le=5), AfterValidator(_half_steps)]  # strict: ang true o "4" ay hindi bilang

def _blank_to_none(value):
    # optional na comment: kapag walang laman o puro espasyo, gawing None
    if isinstance(value, str):
        return value.strip() or None
    return value

Comment = Annotated[Annotated[str, Field(max_length=255)] | None, BeforeValidator(_blank_to_none)]


class RatingUpsert(BaseModel):
    # PUT: gagawa ng bago o papalitan ang dati mong rating sa user na iyon sa server na iyon
    score: Score
    comment: Comment = None

class ServerBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str

class RatingResponse(BaseModel):
    # I-load ang rater, rated at server (selectinload) bago i-validate, kung hindi ay MissingGreenlet
    model_config = ConfigDict(from_attributes=True)

    id: int
    score: float
    comment: str | None = None
    created_at: datetime  # kailan unang nag-rate; hindi nagbabago kapag binago ang score
    server: ServerBrief
    rater: UserPublic
    rated: UserPublic
