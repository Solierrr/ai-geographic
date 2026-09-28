from datetime import datetime

from pydantic import BaseModel, Field


class UserMemorySchema(BaseModel):
    user_id: str
    facts: list[str] = Field(default_factory=list)
    updated_at: datetime
