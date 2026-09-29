# Arquitetura do Repositório

Este serviço expõe um assistente de informações geográficas por uma API
FastAPI. O fluxo usa LangGraph, guardrails de entrada e saída, memória de
conversa (checkpointer Mongo) e memória de longo prazo (perfil de fatos do
usuário). O assistente responde diretamente às solicitações aprovadas.

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,fastapi,langchain,mongodb,redis" height="48" alt="Arquitetura">
  </a>
</p>

- Fluxo LangGraph (`src/workflow/graph/graph.py`): `input_guardrail` →
  `condense_memory` → `orchestrator` → `judge` → `output_guardrail`.
- O `orchestrator` produz a resposta; o `judge` revisa a resposta e pode
  solicitar uma nova tentativa. Os guardrails verificam entrada e saída.
- Integrações de infraestrutura ficam em `src/infra/` (Mongo, Redis, MCP,
  api-messenger); nenhuma delas depende do domínio específico do assistente.
- Autenticação via JWT emitido pelo `api-auth` (`src/core/security/jwt.py`).

```Tree do Repositório (resumo)
├── .github/
│   └── pull_request_template.md
├── src/
│   ├── agents/       # prompts do assistente e do juiz
│   ├── api/          # FastAPI (rotas, schemas)
│   ├── core/         # config, llm, guardrails, logging, security
│   ├── infra/        # clientes de infraestrutura (mongo, redis, mcp, api-messenger)
│   ├── memory/        # checkpointer de sessão
│   └── workflow/     # grafo LangGraph, nodes, state
├── tests/
├── README.md
├── ARCHITECTURE.md
├── RUNNING.md
├── LICENSE
└── ...
```
