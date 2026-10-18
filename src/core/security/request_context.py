"""Identidade da requisição em andamento.

O JWT do usuário fica em uma variável de contexto, e não no estado do grafo, porque
o estado é gravado no checkpointer (Mongo) e o token não pode ser persistido."""

from contextvars import ContextVar

current_user_token: ContextVar[str | None] = ContextVar(
    "current_user_token", default=None
)
