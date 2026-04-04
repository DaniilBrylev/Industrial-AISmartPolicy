from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CriticalityLevel, EnvironmentType


class AssetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    asset_type: str = Field(..., min_length=1, max_length=128)
    environment_type: EnvironmentType
    owner_name: str = Field(..., min_length=1, max_length=255)
    criticality: CriticalityLevel
    network_location: str | None = Field(None, max_length=512)
    description: str | None = None


class AssetCreate(AssetBase):
    department_id: int


class AssetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=255)
    asset_type: str | None = Field(None, min_length=1, max_length=128)
    environment_type: EnvironmentType | None = None
    owner_name: str | None = Field(None, min_length=1, max_length=255)
    criticality: CriticalityLevel | None = None
    network_location: str | None = Field(None, max_length=512)
    description: str | None = None


class AssetRead(AssetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    created_at: datetime
    updated_at: datetime
