from pydantic import BaseModel
from datetime import datetime


class MessageSchema(BaseModel):
    conversation_id: str
    role: str
    content: str
    agent: str | None = None
    timestamp: datetime
    metadata: dict = {}