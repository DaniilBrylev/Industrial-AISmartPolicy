from typing import Literal

from pydantic import BaseModel, Field


class DeleteStatusResponse(BaseModel):
    status: Literal["ok"] = "ok"
    message: str = Field(..., min_length=1)
