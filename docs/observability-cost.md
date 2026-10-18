# Custo de LLM na observabilidade

## Custo por step

Cada chamada de LLM registrada pelo `StepTracker` (`llm_call`) carrega
`costUsd`: o custo em dólar daquela chamada específica, calculado a partir
de `tokensIn`/`tokensOut` e da tabela de preços em
`src/core/config/model_pricing.py`.

- Preço é por modelo, em USD por 1.000 tokens (`in`/`out` separados).
- Match do modelo é exato primeiro, depois por prefixo (alguns providers
  retornam o nome do modelo com sufixo de versão em `response_metadata`).
- Modelo sem pricing cadastrado cai no default (custo `0.0`) e loga um
  warning — não quebra o fluxo principal.
- `tool_call` sempre manda `costUsd: 0.0` (tool não consome tokens de LLM).
- Erro de LLM (`on_llm_error`) também manda `costUsd: 0.0`, já que não há
  como saber quantos tokens foram efetivamente cobrados numa chamada que
  falhou.

Os valores de `MODEL_PRICING` precisam ser conferidos periodicamente contra
a página de pricing de cada provider — eles mudam sem aviso e isso não tem
como ser validado por teste automatizado. Um modelo com pricing zerado em
produção significa que ninguém revisou o TODO no arquivo.

## Fora de escopo — fica pra camada de BI/data mart

`costUsd` aqui é granular (uma linha por chamada de LLM). Agregação fica
pro data mart, não pra esse serviço:

- ROI e custo por resolução de conversa — precisa agregar todos os steps
  de uma `conversationId` e cruzar com o desfecho da conversa.
- Projeção de custo mensal/por período — agregação sobre `costUsd` e
  `timestamp`.

## Compatibilidade com o api-messenger

`costUsd` chega ao `api-messenger` via `LlmObservabilityRequestDTO`. Esse
campo é **opcional** no DTO (sem `@NotNull`) e o DTO usa
`@JsonIgnoreProperties(ignoreUnknown = true)` — de propósito, não por
descuido:

- Sem `@NotNull`: uma versão do `ai-assistant` que ainda não manda
  `costUsd` não tem o request rejeitado pelo `@Valid`. O `api-messenger`
  persiste `0.0` nesse caso (`LlmObservabilityService.ingest`).
- Com `ignoreUnknown`: uma versão do `api-messenger` que ainda não conhece
  `costUsd` não quebra o parse ao receber o campo de um `ai-assistant`
  já atualizado.

Isso existe pra que a ordem de deploy entre os dois serviços não importe.
Sem essa dupla proteção, subir qualquer um dos dois lados primeiro derruba
a ingestão de observabilidade inteira (não só o campo de custo) durante a
janela entre os deploys — vale manter esse padrão pra qualquer campo novo
que cruzar essa fronteira no futuro.
