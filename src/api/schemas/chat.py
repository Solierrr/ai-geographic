from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """O que o cliente envia no POST /chat."""

    conversation_id: str = Field(..., examples=["b2b-empresa-42"])
    message: str = Field(..., min_length=1, examples=["Preciso de um instalador em SP"])


class ChatResponse(BaseModel):
    """O que a API devolve no POST /chat."""

    response: str
    specialists_used: list[str] = Field(default_factory=list)
    workflow_steps: list[str] = Field(default_factory=list)
