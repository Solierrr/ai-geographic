from src.agents.base import base_prompt


def test_build_system_prompt_combina_blocos_obrigatorios(monkeypatch):
    monkeypatch.setattr(base_prompt, "SYSTEM_CORE_SECURITY", "  SEGURANCA  ")
    monkeypatch.setattr(base_prompt, "SYSTEM_CORE_COMMUNICATION", "  COMUNICACAO  ")

    resultado = base_prompt.build_system_prompt(
        "  PROMPT ESPECIFICO  ", include_date=False
    )

    assert resultado == "SEGURANCA\n\nCOMUNICACAO\n\nPROMPT ESPECIFICO"


def test_build_system_prompt_inclui_contextos_opcionais(monkeypatch):
    monkeypatch.setattr(base_prompt, "SYSTEM_CORE_SECURITY", "SEGURANCA")
    monkeypatch.setattr(base_prompt, "SYSTEM_CORE_COMMUNICATION", "COMUNICACAO")
    monkeypatch.setattr(base_prompt, "get_temporal_context", lambda: "DATA")
    monkeypatch.setattr(
        base_prompt,
        "get_user_context",
        lambda user_type, details: f"USUARIO={user_type}:{details['empresa']}",
    )

    resultado = base_prompt.build_system_prompt(
        "AGENTE",
        user_type="fornecedor",
        user_details={"empresa": "ExemploCorp"},
    )

    assert resultado == (
        "SEGURANCA\n\nCOMUNICACAO\n\nAGENTE\n\nDATA\n\n"
        "USUARIO=fornecedor:ExemploCorp"
    )


def test_build_system_prompt_omite_padrao_de_comunicacao(monkeypatch):
    monkeypatch.setattr(base_prompt, "SYSTEM_CORE_SECURITY", "SEGURANCA")
    monkeypatch.setattr(base_prompt, "SYSTEM_CORE_COMMUNICATION", "COMUNICACAO")

    resultado = base_prompt.build_system_prompt(
        "GUARDRAIL", include_communication_standards=False, include_date=False
    )

    assert resultado == "SEGURANCA\n\nGUARDRAIL"
