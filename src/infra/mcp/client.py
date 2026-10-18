"""Cliente MCP do Google Maps (Grounding Lite): carrega as tools uma vez só e as
reaproveita, evitando reconectar a cada chamada de agente."""

import logging

from langchain_mcp_adapters.client import MultiServerMCPClient

from src.core.config.settings import settings

logger = logging.getLogger(__name__)

_tools_cache: list | None = None


async def _carregar_tools() -> list:
    if not settings.GOOGLE_MAPS_API_KEY:
        raise RuntimeError("GOOGLE_MAPS_API_KEY não configurada")
    client = MultiServerMCPClient(
        {
            "google-maps": {
                "url": settings.MAPS_MCP_URL,
                "transport": "streamable_http",
                "headers": {"X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY},
            }
        }
    )
    return await client.get_tools()


async def get_mcp_tools() -> list:
    """Carrega as tools do MCP do Maps na primeira chamada, reaproveita depois."""
    global _tools_cache
    if _tools_cache is None:
        _tools_cache = await _carregar_tools()
    return _tools_cache


async def get_mcp_tool(nome: str):
    """Filtra uma tool específica pelo nome."""
    tools = await get_mcp_tools()
    return [t for t in tools if t.name == nome]


async def get_mcp_tools_by_name(*nomes: str) -> list:
    """Filtra várias tools pelo nome e avisa no log quando alguma não existe no
    servidor, para um nome desatualizado não deixar o especialista sem ferramenta
    e sem nenhum erro."""
    tools = await get_mcp_tools()
    encontradas = [t for t in tools if t.name in nomes]
    ausentes = set(nomes) - {t.name for t in encontradas}
    if ausentes:
        logger.warning("Tools MCP ausentes no servidor: %s", sorted(ausentes))
    return encontradas
