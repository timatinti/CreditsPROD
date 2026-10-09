from typing import Any
from pydantic import BaseModel, Field


class Credentials(BaseModel):
    client_id: str = Field(min_length=3, max_length=128, pattern=r"^\S+$")
    password: str = Field(min_length=8, max_length=128)


class DraftPatch(BaseModel):
    field: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    value: Any = None
    version: int = Field(ge=0)
