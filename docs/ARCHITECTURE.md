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

## Diagrama de arquitetura

### Onde o serviço se encaixa

O `ai-geographic` atende o profissional em campo pelo app mobile. Lugares, clima e rotas vêm do MCP do Google Maps; o potencial solar vem do `api-google`; dúvidas de produto são delegadas por A2A ao `ai-assistant`, repassando o JWT do profissional. O serviço só consome A2A: não publica Agent Card, porque nenhum agente delega a ele.

```mermaid
flowchart LR
    MOB(["app mobile<br/>profissional em campo"]) -->|"POST /chat + JWT"| GEO

    subgraph GEO["ai-geographic (FastAPI + LangGraph)"]
        G["grafo de agentes"]
    end

    GEO -->|MCP| MAPS["Google Maps<br/>lugares, clima e rotas"]
    GEO -->|"viabilidade solar<br/>X-Service-Key"| APIG["api-google"]
    GEO ==>|"A2A + JWT do profissional<br/>persona profissional"| ASS["ai-assistant"]
    GEO --> MONGO[("MongoDB<br/>checkpoints e memória")]
    GEO --> MSG["api-messenger<br/>mensagens e passos do turno"]
    GEO --> LLM["Gemini, Groq, OpenAI"]
    GEO -. valida JWT .-> AUTH["api-auth"]
```

### Grafo de um turno

```mermaid
flowchart TD
    START([mensagem do profissional]) --> IG["input_guardrail"]
    IG -->|"bloqueada"| END0(["REFUSED<br/>ou DEGRADED se o guardrail falhou"])
    IG -->|permitida| CM["condense_memory"]
    CM --> R{"router"}

    R --> RP["route_planner<br/>rota até o cliente (MCP Maps)"]
    R --> FC["field_conditions<br/>clima, luz do dia e potencial solar<br/>(MCP Maps + api-google)"]
    R --> PA["product_advisor<br/>delegação A2A ao ai-assistant"]

    RP --> R
    FC --> R
    PA --> R

    R -->|"responde direto<br/>(nenhum especialista necessário)"| OG
    R -->|"informação suficiente, limite de 3<br/>ou resposta inválida do roteador"| ORQ["orchestrator"]
    ORQ --> J{"judge"}
    J -->|"reprovada: 1 nova tentativa"| ORQ
    J -->|aprovada| OG["output_guardrail"]
    J -->|"reprovada de novo"| BL["resposta trocada por<br/>pedido de reformulação"]
    BL --> OG

    OG -->|"resposta revisada"| OK(["ANSWERED<br/>ou TOOL_FAILED se algum<br/>especialista falhou"])
    OG -->|"guardrail falhou:<br/>mensagem genérica"| DG(["DEGRADED<br/>GUARDRAIL_UNAVAILABLE"])

    classDef ok fill:#d4edda,stroke:#28a745,color:#000
    classDef recusa fill:#f8d7da,stroke:#dc3545,color:#000
    classDef aviso fill:#fff3cd,stroke:#e0a800,color:#000
    class OK ok
    class END0 recusa
    class DG aviso
```

Como no `ai-assistant`, cada especialista devolve o resultado ao roteador, que escolhe o próximo (até 3 por pedido) ou chama o orquestrador. Falhas de ferramenta não interrompem o turno: o especialista registra o problema e o turno segue, terminando com `outcome = TOOL_FAILED` e o motivo (`MAPS_UNAVAILABLE`, `SOLAR_DATA_UNAVAILABLE`, `PRODUCT_ADVISOR_UNAVAILABLE`), não erro HTTP.

### Como o resultado do turno é decidido

O `/chat` responde 200 e informa o desfecho em `outcome` e `reason` (`src/workflow/outcome.py`). A ordem de decisão é esta:

```mermaid
flowchart TD
    S(["fim do turno"]) --> A{"input_guardrail<br/>bloqueou?"}
    A -->|"falha_avaliacao_guardrail"| D1(["DEGRADED<br/>GUARDRAIL_UNAVAILABLE"])
    A -->|"outra categoria"| R1(["REFUSED<br/>OUT_OF_SCOPE, MANIPULATION_ATTEMPT,<br/>INTERNAL_DATA_REQUEST ou FALSE_INFORMATION"])
    A -->|não| B{"o guardrail de saída<br/>falhou?"}
    B -->|sim| D1
    B -->|não| C{"algum especialista<br/>registrou falha?"}
    C -->|sim| T(["TOOL_FAILED<br/>MAPS_UNAVAILABLE, SOLAR_DATA_UNAVAILABLE<br/>ou PRODUCT_ADVISOR_UNAVAILABLE"])
    C -->|não| OK(["ANSWERED"])

    classDef ok fill:#d4edda,stroke:#28a745,color:#000
    classDef recusa fill:#f8d7da,stroke:#dc3545,color:#000
    classDef aviso fill:#fff3cd,stroke:#e0a800,color:#000
    class OK ok
    class R1 recusa
    class D1,T aviso
```
