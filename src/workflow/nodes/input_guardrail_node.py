from ai_lib.guardrails import make_input_guardrail_node

from src.agents.base.base_prompt import build_system_prompt
from src.core.guardrails.prompt import _PROMPT_CLASSIFICADOR
from src.core.llm.llm_groq import llm_groq
from src.workflow.state import GraphState

INPUT_GUARDRAIL_PROMPT = build_system_prompt(
    _PROMPT_CLASSIFICADOR, include_communication_standards=False, include_date=False
)

BLOCKED_RESPONSE = (
    "Desculpe, não posso processar essa solicitação por políticas de segurança."
)

OUT_OF_SCOPE_RESPONSE = (
    "Posso ajudar a localizar um destino específico ou planejar um deslocamento. "
    "Informe origem e destino se quiser uma rota."
)

PENDING_TRIP_CONTEXT = (
    "Há uma solicitação geográfica pendente nesta conversa. "
    "Uma resposta curta que complete endereço, origem, destino, meio de transporte, "
    "horário ou escolha um dos lugares mostrados pode ser APROVADO. "
    "Continue aplicando as regras de segurança e escopo normalmente."
)


def _pending_trip_context(state: GraphState) -> str:
    if state.get("trip_request") or state.get("location_candidates"):
        return PENDING_TRIP_CONTEXT
    return ""


input_guardrail_node = make_input_guardrail_node(
    prompt=INPUT_GUARDRAIL_PROMPT,
    llm=lambda: llm_groq(),
    blocked_response=BLOCKED_RESPONSE,
    blocked_responses={"FORA_ESCOPO": OUT_OF_SCOPE_RESPONSE},
    extra_context=_pending_trip_context,
)
