from src.agents.base.system_prompt import (
    SYSTEM_CORE_COMMUNICATION,
    SYSTEM_CORE_SECURITY,
    get_temporal_context,
    get_user_context,
)


def build_system_prompt(
    specific_prompt: str,
    include_communication_standards: bool = True,
    user_type: str | None = None,
    user_details: dict | None = None,
    include_date: bool = True,
) -> str:
    """Monta o system prompt final combinando SYSTEM_CORE, o prompt
    específico do agente e o contexto temporal/de usuário quando aplicável.
    Único lugar do projeto que deve concatenar esses blocos."""
    parts = [SYSTEM_CORE_SECURITY.strip()]

    if include_communication_standards:
        parts.append(SYSTEM_CORE_COMMUNICATION.strip())

    parts.append(specific_prompt.strip())

    if include_date:
        parts.append(get_temporal_context().strip())

    if user_type:
        parts.append(get_user_context(user_type, user_details or {}).strip())

    return "\n\n".join(parts)
