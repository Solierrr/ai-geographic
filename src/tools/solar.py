import httpx
from langchain_core.tools import tool

from src.core.config.settings import settings
from src.workflow.outcome import Outcome, Reason, record_issue

_TIMEOUT_SEGUNDOS = 20.0
_SEGMENTOS_MOSTRADOS = 3


def _headers() -> dict[str, str]:
    if settings.REGISTRY_CONSUMER_TOKEN:
        return {"Authorization": f"Bearer {settings.REGISTRY_CONSUMER_TOKEN}"}
    return {}


def _resumir(dados: dict) -> dict:
    segmentos = sorted(dados.get("roof_segments", []), key=lambda s: -s["area_m2"])
    return {
        "data_da_imagem": dados["imagery_date"],
        "area_util_do_telhado_m2": dados["usable_roof_area_m2"],
        "maximo_de_paineis": dados["max_panel_count"],
        "horas_de_sol_por_ano": dados["annual_sunshine_hours"],
        "maiores_planos_do_telhado": [
            {
                "inclinacao_graus": s["pitch_degrees"],
                "azimute_graus": s["azimuth_degrees"],
                "area_m2": s["area_m2"],
            }
            for s in segmentos[:_SEGMENTOS_MOSTRADOS]
        ],
    }


@tool
async def consultar_viabilidade_solar(latitude: float, longitude: float) -> dict:
    """Viabilidade solar do telhado mais próximo de uma coordenada (Solar API do Google):
    área útil, quantidade máxima de painéis, horas de sol direto por ano e os maiores planos
    do telhado com inclinação e azimute (0 = norte). Use as coordenadas devolvidas por
    resolve_names. É uma estimativa por imagem de satélite, não um estudo de projeto."""
    try:
        async with httpx.AsyncClient(
            base_url=settings.REGISTRY_URL,
            timeout=_TIMEOUT_SEGUNDOS,
            headers=_headers(),
        ) as client:
            resposta = await client.get(
                "/v1/solar/roof-viability",
                params={"latitude": latitude, "longitude": longitude},
            )
    except httpx.HTTPError:
        record_issue(Outcome.TOOL_FAILED, Reason.SOLAR_DATA_UNAVAILABLE)
        return {"erro": "Não consegui consultar a viabilidade solar agora."}
    if resposta.status_code == 404:
        return {"erro": "Não há cobertura de dados solares do Google para esse ponto."}
    if resposta.status_code >= 400:
        record_issue(Outcome.TOOL_FAILED, Reason.SOLAR_DATA_UNAVAILABLE)
        return {"erro": "Não consegui consultar a viabilidade solar agora."}
    return _resumir(resposta.json())
