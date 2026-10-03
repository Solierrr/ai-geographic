# Arquitetura do Repositório

Este serviço expõe um assistente de deslocamentos por uma API FastAPI. O fluxo
mantém a arquitetura existente: LangGraph, guardrails de entrada e saída,
checkpointer Mongo e memória de conversa. O orquestrador extrai a intenção,
o especialista de rotas decide com dados consultados e o juiz revê a resposta.

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,fastapi,langchain,mongodb,redis" height="48" alt="Arquitetura">
  </a>
</p>

- Fluxo LangGraph (`src/workflow/graph/graph.py`): `input_guardrail` →
  `condense_memory` → `orchestrator` → resolução da localização → capability
  (`routes`/`weather`, `timezone` ou `solar`) → `output_guardrail` → `judge`.
  Casos de esclarecimento, localização simples e fora do escopo pulam as
  consultas desnecessárias.
- Orquestrador, especialista e juiz compartilham o estado tipado do grafo.
  Localização, rotas e clima são etapas de ferramenta, não agentes LLM extras.
  A revisão pode solicitar uma nova tentativa; depois do limite, bloqueia.
- Resultados completos de Maps/Weather/Registry, coordenadas resolvidas e a
  geometria da rota usam canais não persistidos do LangGraph. Somente IDs de lugares candidatos ficam no
  estado para escolhas como “o primeiro”. Mensagens da conversa continuam no
  checkpointer e no serviço de mensagens conforme a retenção configurada.
- `src/infra/external/google_registry/` consome Address, Geo e Solar por DTOs
  tipados e traduz erros do serviço. O cliente HTTP é reutilizado e fechado
  no lifespan. Routes e Weather permanecem temporariamente locais em
  `google_geographic.py`, atrás de contratos estáveis. `GOOGLE_MAPS_API_KEY`
  continua necessária apenas para essas duas integrações locais.
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
