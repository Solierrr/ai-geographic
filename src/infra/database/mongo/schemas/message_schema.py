from datetime import datetime

from pydantic import BaseModel


class MessageSchema(BaseModel):
    conversation_id: str
    role: str
    content: str
    agent: str | None = None
    timestamp: datetime
    metadata: dict = {}
