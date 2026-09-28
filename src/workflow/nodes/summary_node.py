from langchain_core.messages import HumanMessage, RemoveMessage

from src.core.llm import llm_groq
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent

COMPACT_PROMPT = """
Você é um assistente encarregado de manter um resumo conciso de uma conversa em andamento.
Abaixo está o resumo atual (se houver) e as novas mensagens que precisam ser integradas a ele.
Crie um novo resumo combinando tudo de forma clara e focada nos pontos essenciais de finanças/agenda.

Resumo Atual:
{resumo_atual}

Novas Mensagens para incorporar:
{novas_mensagens}

Novo Resumo Final:
"""


def condense_history_node(state: GraphState, config=None) -> dict:
    message_history = state.get("messages", [])
    current_summary = state.get("summary", "")

    # Se tiver menos de 5 mensagens, não faz nada e segue o fluxo
    if len(message_history) <= 5:
        return {}

    # Vamos deixar as 2 últimas mensagens vivas (para manter o contexto imediato do chat)
    # e resumir todas as anteriores.
    messages_to_summarize = message_history[:-2]
    # Formata as mensagens antigas em formato de texto para o LLM ler
    messages_text = ""
    for msg in messages_to_summarize:
        author = "Usuário" if msg.type == "human" else "Assistente"
        messages_text += f"{author}: {msg.content}\n"

    # Chama o LLM para gerar o novo resumo consolidado
    formatted_prompt = COMPACT_PROMPT.format(
        resumo_atual=current_summary if current_summary else "(Nenhum resumo ainda)",
        novas_mensagens=messages_text,
    )

    new_summary = (
        llm_groq()
        .invoke([HumanMessage(content=formatted_prompt)], config=config)
        .content.strip()
    )

    # Cria uma lista de comandos de remoção para as mensagens que foram resumidas
    removal_commands = [RemoveMessage(id=msg.id) for msg in messages_to_summarize]

    # Retorna o novo resumo atualizado e a ordem de apagar as mensagens antigas
    return {
        "summary": new_summary,
        "messages": removal_commands,
        "turn_agents": append_turn_agent(state, "memory_condenser"),
    }
