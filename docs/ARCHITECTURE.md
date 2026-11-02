<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# Arquitetura

A API FastAPI executa um grafo LangGraph com guardrails, resumo, roteamento, especialistas, orquestração e revisão. A fonte principal é o [grafo](https://github.com/Solierrr/ai-geographic/blob/main/src/workflow/graph/graph.py).

```mermaid
flowchart LR
 C[Cliente] -->|HTTP e JWT| A[FastAPI]
 A --> G[LangGraph]
 G --> M[(MongoDB)]
 G -->|MCP HTTP e chave Google| MAP[Google Maps]
 G -->|HTTP e X-Service-Key| SOL[api-google]
 G -->|A2A e JWT| ASS[ai-assistant]
 G -->|HTTP e X-Service-Key| MSG[api-messenger]
 G --> L[Provedores de linguagem]
```

As rotas e os schemas ficam em `src/api/`, o grafo e os seus nós em `src/workflow/` e os prompts em `src/agents/`. Os clientes externos e a persistência ficam em `src/infra/`, enquanto as configurações e a validação do JWT ficam em `src/core/`.

| Integração | Protocolo e autenticação |
|---|---|
| Cliente para `/chat` | HTTP com Bearer JWT validado pelo JWKS do `api-auth` |
| Google Maps | MCP `streamable_http`, configurado em `MAPS_MCP_URL` |
| `api-google` | HTTP com `X-Service-Key` e suporte ao token legado configurado |
| `ai-assistant` | A2A com JWT do profissional e persona `profissional` |
| `api-messenger` | Rotas internas HTTP com `X-Service-Key` |

O especialista de produtos usa a biblioteca A2A para delegar ao assistente principal, mas este serviço não publica um Agent Card próprio. Os detalhes da memória estão em [MONGO.md](../database/MONGO.md), e as integrações seguem o [mapa central](https://github.com/Solierrr/docs-warehouse/blob/main/docs/flows/INTEGRATIONS.md).

O `/health` informa se o processo está no ar e a versão lida de `version.txt`, enquanto o `/ready` testa o Mongo com limite de dois segundos e deixa os modelos de linguagem de fora, porque eles têm alternativa em caso de falha. A instrumentação OpenTelemetry é iniciada pela aplicação e pode ser desligada com `OTEL_SDK_DISABLED`.