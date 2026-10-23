# Modo debug (`POST /debug/chat`)

Roda um turno do agente de campo e devolve, junto da resposta, o que cada nó do
grafo recebeu e devolveu e cada chamada de LLM feita dentro dele. É para o playground
do sandbox e para uso interno; não faz parte do contrato do `/chat` e não aparece no OpenAPI.

## Segurança

A rota responde `404` quando qualquer uma das condições abaixo falha, sem revelar que existe:

- `DEBUG_ADMIN_SUBS` tem ao menos um UUID válido. Não há outra flag: o modo está sempre
  ativo, e esvaziar a lista é o que o desliga.
- `ENVIRONMENT` é `LOCAL`, `DEV`, `QA` ou `PROD` (sem diferenciar maiúsculas). É uma
  lista de permitidos: um valor desconhecido (`PRD`, `staging`, vazio) bloqueia, mesmo
  com admins configurados.

Em PROD o modo funciona como nos outros ambientes, e quem controla o acesso é
`DEBUG_ADMIN_SUBS`: sem admins listados a rota responde 404; para fechá-la de novo,
esvazie a lista. O turno usa o grafo e os
LLMs reais, com a identidade do admin: gasta cota e custo reais, e as consultas a
Maps, clima e registry são dados reais. Em PROD, use só contas de teste.

Depois disso, o JWT é validado pelo mesmo JWKS do `/chat`:

| Situação | Status |
|---|---|
| Sem `Authorization: Bearer` ou token inválido | `401` |
| `sub` fora de `DEBUG_ADMIN_SUBS` (ou lista vazia) | `403` |

Cada turno autorizado deixa uma linha de log com o `sub` e o ambiente
(`Turno de debug (sub=..., ambiente=...)`), para ter rastro de quem usou.

`DEBUG_ADMIN_SUBS` é uma lista de UUIDs separados por vírgula. Entradas que não são
UUID são ignoradas; lista vazia (ou só com entradas inválidas) fecha a rota com 404.

## Requisição

Mesmo corpo do `/chat`:

```json
{ "conversation_id": "t1", "message": "Qual a rota até o cliente em Campinas?" }
```

O token do usuário é repassado ao turno como no `/chat`, então as ferramentas (rotas,
clima, viabilidade do telhado) rodam de verdade, com o JWT dele.

## Resposta

```json
{
  "response": "...",
  "specialists_used": ["route_planner"],
  "workflow_steps": ["router", "route_planner"],
  "debug": {
    "environment": "QA",
    "persisted": false,
    "duration_ms": 1840.2,
    "route": "route_planner",
    "judge": { "status": "approved", "retries": 0 },
    "nodes": [
      {
        "order": 1,
        "node": "router",
        "started_at": "2026-10-21T12:00:00+00:00",
        "duration_ms": 412.5,
        "status": "ok",
        "input": { "message_count": 1, "last_message": { "type": "human", "content": "..." } },
        "output": { "route": "route_planner" },
        "llm_calls": [
          {
            "model": "llama-3.3",
            "prompt": [{ "type": "human", "content": "..." }],
            "completion": "ROTA: route_planner",
            "tokens_in": 120,
            "tokens_out": 4,
            "latency_ms": 380.1,
            "error": null
          }
        ],
        "error": null
      }
    ],
    "llm_calls_outside_nodes": [],
    "truncated": false
  }
}
```

- `nodes` segue a ordem de execução. Um nó que roda de novo (por exemplo depois de um
  retry do `judge`) aparece como outro registro.
- `output` é o que o nó devolveu ao estado; por isso `route`, `judge_status`,
  `judge_retries` e `turn_agents` aparecem sem código por nó.
- `input` traz só as chaves de controle do estado, a quantidade de mensagens e a
  última mensagem, não o histórico inteiro.
- `tokens_*` e `model` podem vir `null` quando o provedor não informa.
- Se o turno falha, a rota devolve `500` com `{ "detail": "...", "debug": {...} }`,
  e o `debug` traz o que foi coletado até ali.

## Delegação ao ai-assistant

O nó que delega a escolha de produtos ao `ai-assistant` (A2A) continua chamando o serviço
de verdade, com o JWT do usuário; essa chamada usa o fluxo normal do `ai-assistant` (não o
modo debug dele) e aparece aqui só como a saída do nó.

## Limites e privacidade

- CPF, CNPJ, telefone e e-mail são trocados por `[CPF]`, `[CNPJ]`, `[TELEFONE]` e
  `[EMAIL]` em todo o bloco `debug`.
- `pii_map`, `user_id` e `user_memory` do estado nunca são copiados.
- Cada texto é cortado em 4.000 caracteres e o bloco `debug` tem teto de 256 KB
  (os limites por campo diminuem até caber). Quando algo é cortado, `truncated` é `true`.
  Se mesmo assim passar do teto, as entradas e os prompts são omitidos.
- Nada do debug é persistido: ele existe só na resposta do turno.

## O que o modo debug não grava

O turno roda com `persist=False`: não cria conversa nem grava mensagens no
`api-messenger`, não registra os steps de observabilidade, não lê nem atualiza a
memória de longo prazo. Uma ressalva: o estado do grafo
continua indo para o checkpointer, na thread `debug:<sub>:<conversation_id>`,
separada das conversas reais.

## CORS

Para o portal chamar este serviço pelo navegador (o `/chat` e o `/debug/chat`), o
app libera as origens de `CORS_ALLOWED_ORIGINS` (separadas por vírgula; sem
credenciais, métodos `GET/POST/PUT/PATCH/DELETE/OPTIONS`, cabeçalhos `Authorization`
e `Content-Type`). Sem a variável, valem `localhost` (portas 5173, 3000 e 5174),
`127.0.0.1:5174` e `https://web-sandbox-7ug0.onrender.com`. Não deixe a variável
vazia: vazio libera nenhuma origem.

## Variáveis

| Variável | Padrão | Uso |
|---|---|---|
| `DEBUG_ADMIN_SUBS` | vazio | UUIDs (`sub` do JWT) autorizados, separados por vírgula |
| `CORS_ALLOWED_ORIGINS` | origens locais e web-sandbox | Origens do portal |

Exemplo para testar no QA:

```bash
curl -X POST "$URL/debug/chat" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"conversation_id":"t1","message":"oi"}'
```
