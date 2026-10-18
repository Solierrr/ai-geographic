import asyncio

import httpx
import pytest

from src.core.config.settings import settings
from src.tools import solar

VIABILIDADE = {
    "imagery_date": "2023-05-01",
    "usable_roof_area_m2": 85.5,
    "max_panel_count": 22,
    "annual_sunshine_hours": 1820.0,
    "carbon_offset_factor_kg_mwh": 400.0,
    "roof_segments": [
        {"pitch_degrees": 20, "azimuth_degrees": 0, "area_m2": 30},
        {"pitch_degrees": 18, "azimuth_degrees": 180, "area_m2": 50},
        {"pitch_degrees": 25, "azimuth_degrees": 90, "area_m2": 10},
        {"pitch_degrees": 10, "azimuth_degrees": 270, "area_m2": 5},
    ],
}


@pytest.fixture
def registry(monkeypatch):
    """Substitui o httpx.AsyncClient do módulo por um com transporte simulado."""
    pedidos: list[httpx.Request] = []

    def instalar(handler):
        def interno(request: httpx.Request) -> httpx.Response:
            pedidos.append(request)
            return handler(request)

        original = httpx.AsyncClient

        def fabrica(*args, **kwargs):
            return original(*args, transport=httpx.MockTransport(interno), **kwargs)

        monkeypatch.setattr(solar.httpx, "AsyncClient", fabrica)
        return pedidos

    return instalar


def _consultar(latitude=-22.9, longitude=-47.06):
    return asyncio.run(
        solar.consultar_viabilidade_solar.ainvoke(
            {"latitude": latitude, "longitude": longitude}
        )
    )


def test_resumo_traz_so_o_que_o_agente_precisa(registry):
    pedidos = registry(lambda r: httpx.Response(200, json=VIABILIDADE))

    resultado = _consultar()

    assert resultado["area_util_do_telhado_m2"] == 85.5
    assert resultado["maximo_de_paineis"] == 22
    assert resultado["horas_de_sol_por_ano"] == 1820.0
    assert [s["area_m2"] for s in resultado["maiores_planos_do_telhado"]] == [
        50,
        30,
        10,
    ]
    assert "carbon_offset_factor_kg_mwh" not in resultado
    assert pedidos[0].url.path == "/v1/solar/roof-viability"
    assert pedidos[0].url.params["latitude"] == "-22.9"


def test_token_de_consumidor_vai_no_cabecalho_quando_configurado(registry, monkeypatch):
    monkeypatch.setattr(settings, "REGISTRY_CONSUMER_TOKEN", "token-de-teste")
    pedidos = registry(lambda r: httpx.Response(200, json=VIABILIDADE))

    _consultar()

    assert pedidos[0].headers["Authorization"] == "Bearer token-de-teste"


def test_sem_token_nao_envia_autorizacao(registry, monkeypatch):
    monkeypatch.setattr(settings, "REGISTRY_CONSUMER_TOKEN", None)
    pedidos = registry(lambda r: httpx.Response(200, json=VIABILIDADE))

    _consultar()

    assert "Authorization" not in pedidos[0].headers


def test_sem_cobertura_devolve_mensagem_clara(registry):
    registry(lambda r: httpx.Response(404, json={"detail": "sem dados"}))

    assert "Não há cobertura" in _consultar()["erro"]


@pytest.mark.parametrize("status", [401, 422, 500, 503])
def test_outros_erros_viram_indisponivel(registry, status):
    registry(lambda r: httpx.Response(status, json={}))

    assert "Não consegui consultar" in _consultar()["erro"]


def test_registry_fora_do_ar_nao_derruba_o_agente(registry):
    def falha(request):
        raise httpx.ConnectError("sem conexão")

    registry(falha)

    assert "Não consegui consultar" in _consultar()["erro"]
