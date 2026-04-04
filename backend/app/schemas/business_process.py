from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BusinessProcessBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    responsible_person: str = Field(..., min_length=1, max_length=255)


class BusinessProcessCreate(BusinessProcessBase):
    department_id: int


class BusinessProcessUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, min_length=1)
    responsible_person: str | None = Field(None, min_length=1, max_length=255)


class BusinessProcessRead(BusinessProcessBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    created_at: datetime
    updated_at: datetime
