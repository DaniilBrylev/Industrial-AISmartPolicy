from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DepartmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    manager_name: str = Field(..., min_length=1, max_length=255)
    contact_info: str = Field(..., min_length=1, max_length=512)
    description: str | None = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=255)
    manager_name: str | None = Field(None, min_length=1, max_length=255)
    contact_info: str | None = Field(None, min_length=1, max_length=512)
    description: str | None = None


class DepartmentRead(DepartmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
