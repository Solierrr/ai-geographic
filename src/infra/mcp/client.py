"""Cliente MCP: conecta no mcp-database e carrega as tools disponíveis, uma
vez só, reaproveitando depois (evita reconectar a cada chamada de agente).
"""

from langchain_mcp_adapters.client import MultiServerMCPClient

from src.core.config.settings import settings

_tools_cache: list | None = None


async def _carregar_tools() -> list:
    client = MultiServerMCPClient(
        {
            "mcp-database": {
                "url": settings.MCP_URL,
                "transport": "streamable_http",
                "headers": {"x-api-key": settings.MCP_API_KEY},
            }
        }
    )
    return await client.get_tools()


async def get_mcp_tools() -> list:
    """Carrega as tools do mcp-database na primeira chamada, reaproveita depois."""
    global _tools_cache
    if _tools_cache is None:
        _tools_cache = await _carregar_tools()
    return _tools_cache


async def get_mcp_tool(nome: str):
    """Filtra uma tool específica pelo nome — cada especialista recebe só
    a ferramenta relevante pro seu domínio, não todas de uma vez."""
    tools = await get_mcp_tools()
    return [t for t in tools if t.name == nome]
