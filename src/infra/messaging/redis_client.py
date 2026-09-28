from redis.asyncio import Redis

from src.core.config.settings import settings

_redis_client: Redis | None = None

# Função assíncrona para que seja chamada por vários usuários diferentes ao mesmo tempo
async def connect_redis() -> Redis:  # Se a conexão funcionar, retorna um objeto Redis
    global _redis_client  # Declarada como private, mas muda para global para conseguir alterar seu valor

    if _redis_client is None:  # Se não houver um client Redis
        client = Redis(
            host=settings.UPSTASH_REDIS_HOST,
            port=settings.UPSTASH_REDIS_PORT,
            username=settings.UPSTASH_REDIS_USERNAME,
            password=settings.UPSTASH_REDIS_PASSWORD,
            ssl=True,
            decode_responses=True,
        )

        try:
            await client.ping()  # Só concluirá a conexão caso o ping com o banco Redis funcionar (deve retornar "PONG")
        except Exception:
            await client.aclose()  # Se der errado, fecha a conexão na mesma hora
            raise
        _redis_client = client
    return _redis_client


def get_redis_client() -> Redis:
    if _redis_client is None:
        raise RuntimeError("Conexão com o Redis ainda não foi estabelecida.")
    return _redis_client


async def close_redis() -> None:
    global _redis_client

    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
