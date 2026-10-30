from pydantic import BaseModel, Field

from src.workflow.outcome import Outcome, Reason


class ChatRequest(BaseModel):
    """O que o cliente envia no POST /chat."""

    conversation_id: str = Field(..., examples=["b2b-empresa-42"])
    message: str = Field(..., min_length=1, examples=["Preciso de um instalador em SP"])


class ChatResponse(BaseModel):
    """O que a API devolve no POST /chat."""

    response: str = Field(..., description="Resposta do copiloto ao profissional.")
    outcome: Outcome = Field(
        ...,
        description="Resultado do turno: respondido, recusado pelo guardrail, degradado ou com ferramenta em falha.",
        examples=["ANSWERED"],
    )
    reason: Reason | None = Field(
        None,
        description="Código do motivo, presente quando outcome não é ANSWERED.",
        examples=["MAPS_UNAVAILABLE"],
    )
    specialists_used: list[str] = Field(default_factory=list)
    workflow_steps: list[str] = Field(default_factory=list)
