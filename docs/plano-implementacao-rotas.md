# Plano de implementação — recomendações de rota com clima

Data da revisão: 2026-09-30. Estado: **primeira versão implementada; integração real depende das credenciais e APIs Google habilitadas**.

## 1. Objetivo e fronteira do produto

O `ai-geographic` deve ajudar uma pessoa a ir de uma origem a um destino, considerando localização, data/hora, duração do trajeto, meio de transporte, preferências explícitas e previsão do tempo disponível. A saída deve recomendar uma rota ou horário **somente quando os dados consultados sustentarem a escolha**. Também pode localizar um destino para preparar uma rota.

- Dentro do escopo: “Como vou do Centro ao Ibirapuera amanhã às 15h?”, “Onde fica o Museu do Ipiranga?”, “Devo sair agora ou mais tarde para ir a pé até a estação?”.
- Fora do escopo: catálogo de estabelecimentos (“liste pizzarias em São Paulo”), turismo genérico e respostas geográficas sem relação com localização ou deslocamento. A resposta fora do escopo oferece ajuda para traçar um deslocamento, sem fazer busca de categorias.
- A primeira entrega produz uma recomendação textual e dados estruturados para um futuro mapa. A escolha entre mapa no app e redirecionamento ao Google Maps fica para outra decisão.
- “Clima” pode influenciar a **janela de saída**, a escolha de meio de transporte ou a comparação entre trajetos quando houver evidência de diferença. Previsão de chuva, por si só, não comprova interdição, alagamento ou segurança de uma via.

## 2. Diagnóstico do código existente

| Parte | Situação atual | Mudança planejada |
| --- | --- | --- |
| `src/workflow/graph/graph.py` | Fluxo linear: entrada → memória → orquestrador → juiz → saída. | Encaminhamentos explícitos para localizar, esclarecer e recomendar rota; revisão da resposta final. |
| `src/workflow/nodes/orchestrator_node.py` | Produz a resposta diretamente em texto. | Produzir uma decisão estruturada (`localizar`, `rota`, `esclarecer`, `fora_escopo`) e responder apenas aos casos simples; sem criar outro agente planejador. |
| `src/workflow/state/state.py` | Estado não contém solicitação de viagem, resultados externos nem evidências. | Acrescentar contratos tipados e campos de resultado/erro por etapa. |
| `src/workflow/nodes/judge_node.py` | Revê conversa e resposta, sem ver resultados de APIs; retry volta ao orquestrador. | Receber evidências e verificar a resposta efetivamente enviada; retry volta ao redator responsável, com limite. |
| `src/workflow/nodes/output_guardrail_node.py` | Pode reescrever a resposta depois do juiz. | Transformar a revisão em aprovação/rejeição: uma reescrita volta ao especialista e passa novamente pela renderização e verificação. Nenhum texto factual muda depois do juiz. |
| `src/core/guardrails/prompt.py` e `src/agents/base/system_prompt.py` | Escopo amplo de “informações geográficas”. | Definir o escopo de deslocamento e os casos permitidos de localização. |
| `src/api/schemas/chat.py` | Recebe só `conversation_id` e `message`. | Permitir, opcionalmente, coordenadas fornecidas pelo app com consentimento e precisão declarada; texto continua funcionando sozinho. |
| `src/workflow/runner.py` e memória | A conversa e fatos duráveis podem reter texto de viagem; checkpointer persiste o estado. | Não transformar origens/destinos precisos ou histórico de trajetos em memória durável; limitar o que vai para logs/checkpoints conforme retenção acordada. |
| `src/infra/mcp/client.py` | Cliente MCP aponta para `mcp-database`, cujas tools não são de mapas/clima. | Não reutilizá-lo como se fornecesse Google Maps. Criar contrato próprio com o serviço de integração escolhido. |
| `google-registry` | No código atual, só expõe a capacidade Solar. | Adicionar contratos/rotas de resolução de lugares, Routes e Weather **antes** de conectar `ai-geographic`, se esse serviço continuar sendo o concentrador Google. |

As chaves de LLM ficam no `google-registry` e o `ai-geographic` as recebe pelo corretor; a credencial Google Maps deve continuar restrita ao serviço integrador e ter nome/configuração próprios.

## 3. Papéis e comunicação

**Três agentes de decisão no desenho inicial:**

1. **Orquestrador existente, adaptado:** classifica intenção, extrai campos com formato validado, pede uma informação essencial quando necessário e encaminha. Não calcula coordenadas ou durações.
2. **Especialista em rotas, novo:** recebe opções e previsão já normalizadas; devolve uma `Decision` estruturada com rota/horário escolhido e justificativas vinculadas a IDs de evidências. Também pode dizer que não há base para distinguir alternativas.
3. **Juiz existente, adaptado desde a primeira entrega:** verifica escopo, consistência e suporte factual na resposta final. Para números, IDs de lugar, duração, horários e condição climática, acrescentar verificação determinística da `Decision` contra o pacote de evidências; o LLM sozinho não serve como prova.

**Capacidades sem agente LLM obrigatório:** resolver lugares, calcular rotas e consultar clima são ferramentas/etapas tipadas. Um especialista de clima só passa a ser um agente próprio quando houver interpretação meteorológica que não caiba em regras testáveis. Isso preserva o contrato de comunicação sem multiplicar decisões livres.

Os participantes se comunicam pelo estado compartilhado do LangGraph, com campos tipados e `requested_action`/`missing_data`. Qualquer etapa pode **solicitar** nova resolução, cálculo ou consulta; o grafo encaminha ao responsável. Não há chamadas diretas arbitrárias entre agentes. Limitar tentativas de resolução, consultas por turno e retornos ao especialista; caso o limite seja atingido, pedir esclarecimento ou explicar a indisponibilidade. Limpar resultados temporários no início de cada turno para não reaproveitar clima ou trânsito antigo da conversa.

Contratos mínimos do estado:

- `TravelRequest`: intenção, origem/destino informados, modo, `time_kind` (`departure`/`arrival`/`now`), instante com fuso, preferências e campos ausentes.
- `ResolvedPlace`: `place_id` quando houver, rótulo, coordenadas, precisão, candidatos e situação de ambiguidade.
- `RouteOption`: ID local, modo, origem/destino, saída/chegada estimadas, distância, duração, passos/trechos necessários, geometria opcional, pedágios quando disponíveis, fonte e momento da consulta.
- `WeatherEvidence`: ponto e instante/intervalo, previsão (e alerta, quando consultado), fonte, consulta, cobertura e ausência/erro explícitos.
- `Decision`: rota/horário escolhido, alternativas realmente recebidas, motivos ligados a IDs de evidência, limitações e `needs_clarification`. Os fatos numéricos da resposta são renderizados a partir dessa estrutura, sem pedir ao LLM que os recopie livremente.
- `ProviderResult`: `ok`, `not_found`, `ambiguous`, `unsupported`, `timeout`, `quota`, `unavailable` ou `invalid_response`; nunca transformar erro em valor vazio que pareça sucesso.

## 4. Fluxo proposto

```text
entrada/anonimização → classificador de escopo → resumo → orquestrador estruturado
    ├─ fora do escopo → resposta curta → guardrail de saída → verificação final → entrega
    ├─ faltam dados → pergunta única e específica → guardrail → verificação final → entrega
    ├─ onde fica X → resolver lugar → resposta factual → guardrail → verificação final → entrega
    └─ rota → resolver origem/destino → obter rota(s) → obter previsão pertinente
             → especialista em rotas → validar decisão → renderizar fatos
             → guardrail de saída → verificação factual + juiz
             → entrega ou uma tentativa controlada de correção
```

1. **Intenção e contexto.** Verificar se o pedido está no escopo. Resolver “aqui”, “amanhã” e referências da conversa apenas se existir localização fornecida no turno ou dado contextual válido. A ausência de geolocalização do app exige pergunta; não presumir posição do usuário.
2. **Tempo.** Converter horário local da origem para UTC na partida e usar o fuso do destino na chegada; distinguir `sair às 9` de `chegar às 9`. Se o usuário não mencionar horário, usar `agora` e dizer isso; se pedir “melhor horário” sem intervalo, pedir a janela desejada. Para chegada de carro/a pé, estimar uma saída por cálculo limitado e recalcular a rota uma vez; apresentar como estimativa. Para transporte público, planejar adaptação específica de `arrivalTime` na etapa futura. Não consultar rota futura para uma data passada.
3. **Localização.** Usar Geocoding para endereço e Places para nome de lugar **pontual**. Se houver mais de um candidato plausível, confirmar qual deles é o destino; não escolher silenciosamente.
4. **Rotas.** Usar `Compute Routes` com modo explícito, horário e máscara de campos mínimos. Pedir alternativas quando suportadas e úteis, mas aceitar uma única rota. Não fabricar alternativas. A primeira entrega cobre origem e destino, sem paradas intermediárias; pedidos com paradas informam a limitação. Na primeira entrega, suportar `DRIVE` e `WALK`; outros modos retornam indisponibilidade do recurso até suas regras específicas serem implementadas. Aplicar o aviso exigido pelo provedor às rotas a pé.
5. **Clima.** Consultar previsão horária para saída/chegada; em trajetos suficientemente longos, amostrar poucos pontos da geometria em horários estimados, sem afirmar precisão contínua ao longo de toda a rota. Se o instante estiver fora do horizonte da previsão, explicar que ainda não há previsão confiável. Dados indisponíveis permitem informar a rota, mas **não** dizer que ela foi escolhida pelo clima.
6. **Decisão.** Primeiro respeitar modo e preferências explícitas; depois comparar duração/condições efetivamente medidas. Sem diferença climática relevante entre alternativas, justificar pela duração ou preferência. Para “melhor horário”, consultar um conjunto pequeno e explícito de horários candidatos, com limite de chamadas e sem prometer ótimo global.
7. **Verificação e saída.** O especialista entrega decisão estruturada, e o renderizador insere coordenadas, distâncias, durações e previsão a partir das evidências validadas. O guardrail de saída só aprova ou rejeita; uma correção volta ao redator e repete renderização/verificação. O juiz confere o texto que será entregue e nada o modifica depois. Falha de revisão bloqueia a recomendação factual e produz resposta de indisponibilidade. A resposta inclui caráter estimado, horário da consulta e atribuições do provedor.

Perguntas de esclarecimento devem desbloquear **um dado de cada vez**, priorizando o primeiro requisito para a próxima consulta:

| Condição | Pergunta curta sugerida |
| --- | --- |
| Origem ausente ou “aqui” sem coordenada autorizada | “De onde você vai sair?” |
| Destino ausente | “Para onde você quer ir?” |
| Lugar com candidatos plausíveis | “Você quer dizer [local A] ou [local B]?” |
| Meio de transporte ausente em pedido de rota | “Vai de carro ou a pé?” |
| “Melhor horário” sem janela | “Entre quais horários você pode sair?” |
| Horário/data com interpretação incerta | “Você quer sair às [hora] ou chegar até [hora]?” |

Se a próxima resposta do usuário preencher o campo, continuar do ponto necessário sem perder a intenção anterior; reconsultar dados voláteis antes de recomendar.

## 5. Dependências e decisões antes de codificar

| Decisão/ponto que pode travar | Padrão recomendado para começar | Confirmação necessária antes da integração real |
| --- | --- | --- |
| Quem chama Google Maps/Weather? | `google-registry` como fachada, com DTOs estáveis; `ai-geographic` consome HTTP interno. | Validar dono, autenticação serviço a serviço, ambiente e cronograma desse repositório. |
| Localização atual do usuário | Coordenada opcional enviada pelo app após permissão; caso contrário, origem textual. | Definir contrato e consentimento no cliente. |
| Modos iniciais | `DRIVE` e `WALK`; modelo de dados extensível a `TRANSIT`/`BICYCLE`. | Confirmar público e prioridade de transporte público. |
| O que o clima muda? | Horário, cautela e escolha quando houver diferença sustentada; não inventar risco de via. | Se o produto quer evitar alagamento/interdição, é necessária outra fonte de incidentes. |
| “Chegar até” | Estimativa de horário de saída para carro/a pé, sem garantia de pontualidade. | Confirmar se o app exige chegada garantida ou somente estimativa. |
| Exibição final | Guardar referência/ID e dados mínimos da rota no contrato de resposta; nenhuma decisão de UI agora. | Antes de exibir conteúdo ou mapa, revisar atribuição e condições do Google. |
| Retenção | Não pôr localização precisa em memória de longo prazo; não registrar payload completo de provedores; revisar TTL do checkpoint. | Definir política de retenção/privacidade do produto. |
| Custos e operação | Field masks mínimos, limites de alternativas e horários, timeout, orçamento por turno, métricas sem coordenadas precisas. | Habilitar APIs, quotas, faturamento e chaves no projeto Google. |

O `openapi.yaml` do repositório descreve um fluxo assíncrono diferente da rota FastAPI atual; antes de publicar a nova interface, regenerar o contrato a partir do código e decidir se `/chat` continua síncrono. Não basear clientes novos nesse arquivo sem conciliá-lo.

## 6. Etapas de implementação e critérios de aceite

1. **Contratos e grafo.** Modelar estado tipado, encaminhamentos e erros; atualizar escopo; garantir limpeza por turno. Aceite: pedidos de rota, localização, esclarecimento e fora do escopo seguem nós distintos em testes com mocks.
2. **Integração de localização.** Criar fachada/adapter, normalização e ambiguidade. Aceite: endereço único resolve; “Shopping Morumbi” com candidatos ambíguos pede escolha; “aqui” sem coordenadas pede origem.
3. **Integração de rotas.** Modos explícitos, alternativas reais, estimativas de saída/chegada e limites. Aceite: zero/uma/várias rotas, chegada solicitada, rota a pé com aviso e falhas do provedor têm respostas distintas.
4. **Integração de clima.** Previsão por ponto/tempo, horizonte e indisponibilidade. Aceite: comparação usa apenas pontos e instantes consultados; previsão fora do horizonte não gera recomendação climática.
5. **Especialista e verificação desde o início.** Recomendação estruturada vinculada a evidências; fatos renderizados do estado validado; guardrail sem reescrita direta; verificador determinístico + juiz final. Aceite: duração ou chuva inventada é rejeitada; correção volta ao redator e percorre a verificação outra vez.
6. **Conversa, privacidade e operação.** Testes de múltiplos turnos, consentimento da localização, memória, quotas, latência, observabilidade e documentação. Aceite: contexto útil persiste, resultados voláteis não; métricas não expõem trajetos precisos; contrato HTTP corresponde ao app.

Testes: unitários de contratos e decisões, integração com respostas simuladas das APIs, fluxo LangGraph ponta a ponta e pequeno conjunto de avaliações de respostas em português. Consultas reais ficam em smoke tests controlados, porque trânsito/clima mudam e não devem tornar a suíte comum instável.

## 7. Revisão adversarial do planejamento

Estas são **simulações de projeto**, não testes de uma implementação. “Falha identificada” significa que a versão do plano anterior à correção não teria resposta definida. Fiz duas rodadas iniciais de cinco perguntas. Como houve falhas, acrescentei uma terceira rodada de cinco após corrigir o plano.

### Rodada inicial 1 — cinco perguntas

| Pergunta do usuário | Análise do plano inicial | Regra adicionada |
| --- | --- | --- |
| “Como chego ao Shopping Morumbi amanhã?” | **Falha:** origem e possível ambiguidade do destino não estavam resolvidas. | Pedir origem; apresentar candidatos ambíguos para confirmação. |
| “Qual rota estará melhor daqui a um mês por causa da chuva?” | **Falha:** não havia limite para horizonte de previsão. | Separar rota de previsão; não inferir clima além do horizonte disponível. |
| “Preciso chegar às 8h, a que horas saio?” | **Falha:** horário de chegada poderia ser confundido com partida. | `time_kind` explícito; estimativa de saída com recálculo limitado. |
| “Liste pizzarias em São Paulo.” | Coberto pelo escopo: não fazer catálogo; oferecer ajuda com deslocamento. | Registrar como teste de regressão do escopo. |
| “Vou a pé; a rota é segura e acessível?” | **Falha:** API de rotas não prova segurança/acessibilidade contínua. | Não garantir; mostrar aviso exigido e explicar falta de dados específicos. |

### Rodada inicial 2 — outras cinco perguntas

| Pergunta do usuário | Análise do plano após a rodada 1 | Regra adicionada |
| --- | --- | --- |
| “Como vou daqui ao aeroporto agora?” | **Falha:** “daqui” depende de coordenadas que o `/chat` ainda não recebe. | Coordenada opcional com consentimento ou pergunta de origem textual. |
| “Está chovendo; desvie das ruas alagadas.” | **Falha:** chuva não identifica ruas interditadas ou alagadas. | Sem fonte de incidentes, informar limite e não prometer desvio seguro. |
| “Qual é a melhor rota se a API de clima cair?” | **Falha:** faltava separar recomendação de rota de recomendação baseada no clima. | Oferecer rota com limitação explícita; não atribuir escolha ao clima. |
| “Onde fica o lugar que citei ontem?” | Contexto pode ajudar, mas resumo/memória não devem ser tomados como identificação atual. | Revalidar o lugar e confirmar se a referência não for inequívoca. |
| “Me mostre três rotas a pé.” | A API pode retornar menos alternativas. | Mostrar só rotas recebidas; nunca completar a lista artificialmente. |

### Rodada adicional 3 — exigida pelas falhas acima

| Pergunta do usuário | Resultado do plano corrigido |
| --- | --- |
| “Vou para Santa Cruz amanhã às 7h; qual cidade você escolheu?” | Pede confirmação quando há mais de um lugar plausível; não consulta rota prematuramente. |
| “Saio às 18h de carro e preciso estar lá às 18h30; você garante?” | Usa duração estimada e informa que trânsito futuro não permite garantia. |
| “Quero ir de ônibus, mas ainda não escolhi a origem.” | Pede origem; informa que `TRANSIT` não integra a primeira entrega sem fingir rota. |
| “Qual rota evita chuva em todo o percurso de 200 km?” | Usa amostras limitadas e declara que não conhece o clima de cada metro/minuto; não promete evitar toda chuva. |
| “Ontem a rota levou 20 minutos; posso usar o mesmo tempo agora?” | Faz nova consulta; não reutiliza trânsito ou previsão guardados no checkpoint. |

Resultado: nenhuma das cinco perguntas da terceira rodada expôs uma **regra de fluxo ainda indefinida**. Isso valida a coerência do plano para os casos analisados, não garante ausência de defeitos na implementação; os testes de aceite acima permanecem obrigatórios.

## 8. Fontes para confirmar na implementação

### Estado da implementação inicial

O fluxo proposto está conectado no grafo existente, com orquestrador,
especialista de rotas e juiz, além das etapas tipadas de lugar, rota e clima.
O `/chat` recebe coordenadas opcionais e fuso do usuário e devolve dados da
rota aprovada. Os testes usam respostas simuladas de Google e incluem
continuidade de escolha de lugar, limites de clima e execução do grafo.

O plano considerava `google-registry` como fachada. Como esse serviço ainda
não oferece os contratos de Maps/Weather, o primeiro adaptador ficou em
`src/infra/external` do próprio `ai-geographic`, preservando a camada de
infraestrutura já presente. A integração poderá migrar para uma fachada
interna quando ela oferecer os mesmos contratos, sem alterar os papéis dos
agentes ou o grafo.

Ainda é preciso validar uma consulta real em ambiente com Places API (New),
Routes API, Time Zone API e Weather API habilitadas, chave restrita e quotas
definidas. O mapa visual e o redirecionamento continuam decisões futuras.

- Google Routes: [Compute Routes e alternativas](https://developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRoutes), [trânsito e horário de partida](https://developers.google.com/maps/documentation/routes/config_trade_offs), [modos e aviso para caminhada/bicicleta](https://developers.google.com/maps/documentation/routes/reference/rest/v2/RouteTravelMode), [políticas e atribuição](https://developers.google.com/maps/documentation/routes/policies).
- Google Weather: [previsão horária](https://developers.google.com/maps/documentation/weather/hourly-forecast), [cobertura](https://developers.google.com/maps/documentation/weather/coverage), [políticas e atribuição](https://developers.google.com/maps/documentation/weather/policies).
- Google Places: [visão geral](https://developers.google.com/maps/documentation/places/web-service/overview), [políticas e atribuição](https://developers.google.com/maps/documentation/places/web-service/policies).

Revalidar documentação, quotas, preços, cobertura e termos antes de ativar as APIs em produção; podem mudar.
