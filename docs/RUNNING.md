<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# Execução local

Use Python 3.14, a versão do [Dockerfile](https://github.com/Solierrr/ai-geographic/blob/main/Dockerfile), `make`, MongoDB e Infisical CLI autenticado. O procedimento comum está em [PYTHON.md](https://github.com/Solierrr/docs-warehouse/blob/main/readme/running/PYTHON.md).

Execute `make install`, `make vault` e `make dev`, sabendo que a exportação do cofre usa as pastas `/database`, `/redis`, `/llm`, `/service-urls`, `/mcp`, `/service-keys`, `/otel`, `/auth` e `/google` e que o comando de desenvolvimento inicia `src.api.app:app` com o Uvicorn.

| Comando | Efeito |
|---|---|
| `make test` | Pytest e cobertura de `src` |
| `make lint` | Ruff em `main.py`, workflow e clientes LLM |
| `make build` | Compilação dos módulos Python |
| `make openapi` | Exportação de `openapi.yaml` |

Abra `/docs` no servidor local. Faça primeiro `GET /ready` e depois uma chamada autenticada a `/chat`. O Mongo é necessário para criar o checkpointer. Fora de `LOCAL`, a ausência de `JWT_JWKS_URL` bloqueia a conversa com 503. Em `LOCAL`, o código permite continuar sem validar a assinatura quando esse endereço não foi configurado. Não use esse comportamento para validar uma integração de autenticação.
