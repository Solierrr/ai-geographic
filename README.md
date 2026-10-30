# ai-geographic

Copiloto de campo do profissional de energia solar (técnicos, instaladores e engenheiros em serviço), usado no app mobile da Solaria. Ele ajuda quem está na rua a planejar a rota até o cliente, a decidir se vale ir a uma região em uma data (clima, chuva, vento e luz do dia) e a ter uma noção aproximada do potencial solar do local. Usa o MCP oficial do Google Maps (lugares, clima e rotas) e, quando a dúvida é sobre produtos, delega ao `ai-assistant` por A2A, repassando o JWT do profissional.

<p>

[![License](https://img.shields.io/github/license/Solierrr/ai-geographic)](https://github.com/Solierrr/ai-geographic/blob/main/LICENSE)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/Solierrr/ai-geographic)](https://github.com/Solierrr/ai-geographic/commits)
[![GitHub Issues](https://img.shields.io/github/issues/Solierrr/ai-geographic)](https://github.com/Solierrr/ai-geographic/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/Solierrr/ai-geographic)](https://github.com/Solierrr/ai-geographic/pulls)
[![Release](https://img.shields.io/github/v/release/Solierrr/ai-geographic)](https://github.com/Solierrr/ai-geographic/releases)

</p>

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,fastapi,langchain,mongodb,docker" height="48" alt="Stack">
  </a>
</p>

## API

| O quê | Caminho | Observação |
|---|---|---|
| Swagger UI | `/docs` | desligado com `DOCS_ENABLED=false` (PROD) |
| Contrato OpenAPI | `/openapi.json` | o mesmo contrato fica versionado em `openapi.yaml`, gerado por `make openapi` e conferido no CI |
| Conversa | `POST /chat` | JWT do `api-auth` em `Authorization: Bearer <token>` |
| Vivo | `GET /health` | `{"status":"UP","version":"X.Y.Z"}` |
| Pronto | `GET /ready` | ping no Mongo; 503 com `{"status":"DOWN"}` quando ele não responde |

Todo erro HTTP sai como `application/problem+json`, com `errorCode` do catálogo de erros do `docs-warehouse`. O que acontece dentro da conversa não é erro: a resposta do turno volta 200 com `outcome` (`ANSWERED`, `REFUSED`, `DEGRADED` ou `TOOL_FAILED`) e `reason`, presente quando `outcome` não é `ANSWERED`:

| `reason` | `outcome` | Quando |
|---|---|---|
| `OUT_OF_SCOPE` | `REFUSED` | pergunta fora do escopo do copiloto |
| `MANIPULATION_ATTEMPT` | `REFUSED` | tentativa de manipular as instruções do agente |
| `INTERNAL_DATA_REQUEST` | `REFUSED` | pedido de dados internos da plataforma |
| `FALSE_INFORMATION` | `REFUSED` | mensagem baseada em informação falsa |
| `GUARDRAIL_REFUSED` | `REFUSED` | recusa do guardrail sem categoria conhecida |
| `GUARDRAIL_UNAVAILABLE` | `DEGRADED` | o guardrail não conseguiu avaliar e a resposta saiu genérica |
| `LLM_FALLBACK` | `DEGRADED` | um provedor de LLM falhou e outro respondeu |
| `MAPS_UNAVAILABLE` | `TOOL_FAILED` | o MCP do Google Maps não respondeu |
| `SOLAR_DATA_UNAVAILABLE` | `TOOL_FAILED` | a viabilidade solar do `api-google` não respondeu |
| `PRODUCT_ADVISOR_UNAVAILABLE` | `TOOL_FAILED` | a delegação ao `ai-assistant` falhou |
| `TOOL_ERROR` | `TOOL_FAILED` | outra ferramenta falhou durante o turno |

### Chamadas a outros serviços

- `api-messenger`: rotas `/internal/**` com `X-Service-Key` (`SERVICE_KEY`).
- `api-google`: viabilidade solar com `X-Service-Key` (`SERVICE_KEY`). Enquanto o `api-google` não exige a chave, o `REGISTRY_CONSUMER_TOKEN`, se definido, segue junto como `Authorization: Bearer`.

### A2A

O A2A não é OpenAPI e fica fora do contrato. Este serviço só consome A2A: quando a dúvida é sobre produtos, o especialista de Produtos delega ao `ai-assistant` (`A2A_ASSISTANT_URL`) pelo cliente da `lib-ai`, repassando o JWT do profissional e a persona `profissional`. O `ai-geographic` não publica Agent Card próprio, porque nenhum agente delega a ele.

## Aprofunde-se no Projeto!

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [RUNNING.md](./RUNNING.md)

## Contribuindo

- Escreva commits em Conventional Commits, em inglês e minúsculas (`feat:`, `fix:` etc.).
- Todo PR deve usar o `.github/pull_request_template.md` deste repositório.
