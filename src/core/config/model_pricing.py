"""Tabela de preços por modelo, usada pra calcular custo em USD por chamada de LLM."""

import logging

logger = logging.getLogger(__name__)

MODEL_PRICING = {
    "gemini-2.5-flash": {"in": 0.0003, "out": 0.0025},
    "openai/gpt-oss-120b": {"in": 0.00015, "out": 0.00060},
}

DEFAULT_PRICING = {"in": 0.0, "out": 0.0}


def get_pricing(model: str) -> dict:
    """Match exato primeiro; depois prefixo (response_metadata às vezes traz
    sufixo de versão). LIMITAÇÃO CONHECIDA: se dois modelos cadastrados
    compartilharem prefixo (ex: "gemini-2.5-flash" e "gemini-2.5-flash-lite"
    com preços diferentes), o match depende da ordem de inserção no dict —
    revisar se isso acontecer."""
    if model in MODEL_PRICING:
        return MODEL_PRICING[model]
    for known_model, pricing in MODEL_PRICING.items():
        if model.startswith(known_model):
            return pricing
    logger.warning("Sem pricing cadastrado para o modelo %s — custo sai 0.0", model)
    return DEFAULT_PRICING
