from datetime import datetime
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator
from utils.enum import TaskPriority

class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    deadline: datetime  # required: NOT NULL sa database
    has_alarm: bool = True

class TaskCreate(TaskBase):
    # kailangan ng timezone (Z o +08:00): ang "2026-10-10T17:00:00" ay hindi malalaman kung anong oras talaga
    deadline: AwareDatetime

class TaskUpsert(TaskBase):
    # PUT /task/{client_id}: ang buong task mula sa app; pwedeng gawa offline kaya galing sa app ang completed_at
    deadline: AwareDatetime
    is_complete: bool = False
    completed_at: AwareDatetime | None = None

class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    priority: TaskPriority | None = None
    deadline: AwareDatetime | None = None
    has_alarm: bool | None = None

    @model_validator(mode="after")
    def no_explicit_null(self):
        # NOT NULL ang lahat ng column na ito: ang hindi ipinadala ay hindi babaguhin, pero hindi puwede ang `null`
        nulls = sorted(f for f in self.model_fields_set if getattr(self, f) is None)
        if nulls:
            raise ValueError(f"{', '.join(nulls)} cannot be null")
        return self

class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uid: int
    client_id: str | None = None  # ang UUID na ginawa ng app; ito ang ID ng task sa app
    is_complete: bool
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

