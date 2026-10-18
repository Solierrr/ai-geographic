from pydantic import BaseModel, Field
from datetime import datetime


class ConversationSchema(BaseModel):
    conversation_id: str
    user_id: int
    user_type: str
    user_details: dict = Field(default_factory=dict)
    active_agent: str
    status: str
    started_at: datetime
    last_interaction_at: datetime
