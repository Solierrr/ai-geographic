# Arquitetura do Repositório

Este serviço segue o mesmo padrão do `ai-assistant`: uma API FastAPI que
expõe um chatbot orquestrado via LangGraph, com guardrails de entrada/saída,
memória de curto prazo (checkpointer Mongo) e memória de longo prazo (perfil
de fatos do usuário), delegando a especialistas de domínio por meio de um
Agente Roteador. Os especialistas são o Planejador de Rotas e o de Condições de Campo, que usam o MCP oficial do Google Maps (Grounding Lite), e o de Produtos, que delega ao `ai-assistant` por A2A repassando o JWT do profissional. Não há banco de dados de negócio: lugares, clima e rotas vêm do Google.

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,fastapi,langchain,mongodb" height="48" alt="Arquitetura">
  </a>
</p>

- Orquestração multiagente via LangGraph (`src/workflow/graph/graph.py`):
  `input_guardrail` → `condense_memory` → `router` → especialista(s) →
  `orchestrator` → `judge` → `output_guardrail`.
- Cada especialista de domínio vive em `src/agents/specialist/<nome>/` (prompt)
  e `src/workflow/nodes/<nome>_node.py` (node). Os especialistas são `route_planner`
  e `field_conditions` (ferramentas do MCP do Google Maps) e `product_advisor`
  (delegação A2A ao `ai-assistant`).
- Integrações de infraestrutura ficam em `src/infra/` (Mongo, MCP,
  api-messenger); nenhuma delas depende do domínio específico do assistente.
- Autenticação via JWT emitido pelo `api-auth` (`src/core/security/jwt.py`).

```Tree do Repositório (resumo)
├── .github/
│   └── pull_request_template.md
├── src/
│   ├── agents/       # framework base + especialistas
│   ├── api/          # FastAPI (rotas, schemas)
│   ├── core/         # config, llm, guardrails, logging, security
│   ├── infra/        # clientes de infraestrutura (mongo, mcp, api-messenger)
│   ├── memory/        # checkpointer de sessão
│   └── workflow/     # grafo LangGraph, nodes, state
├── tests/
├── README.md
├── ARCHITECTURE.md
├── RUNNING.md
├── LICENSE
└── ...
```
