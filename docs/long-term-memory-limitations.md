# Limitações conhecidas — memória de longo prazo

## Race condition entre conversas concorrentes do mesmo usuário

`get_user_memory` é lido no início do turno e `upsert_user_memory` grava no
fim, em background (`asyncio.create_task` em `runner.py`). Se o mesmo
`user_id` tiver dois turnos em andamento ao mesmo tempo (duas abas, dois
canais), o `upsert` de um turno pode sobrescrever o do outro — última
escrita vence, sem merge dos fatos. Não é uma corrupção de dado grave (o
pior caso é perder um fato aprendido num turno concorrente), mas é uma
limitação conhecida, não resolvida por esta implementação.

## Mitigação de PII é só por instrução de prompt

O prompt de extração (`memory_extraction.py`) pede pro LLM nunca incluir
dado sensível (documento, valor financeiro, senha, pagamento), mas isso é
best-effort — não há validação técnica (regex, allowlist de categorias)
depois que o LLM responde. Vale endurecer isso antes de tratar esse dado
como confiável em produção, principalmente dado o domínio financeiro do
produto.

## Índice do Mongo só é criado quando a API sobe

`ensure_user_memory_indexes()` roda no `lifespan` de `src/api/app.py`. O
fluxo de `main.py` (CLI local) não passa por esse `lifespan`, então rodando
só via CLI o índice único em `user_id` nunca é criado por conta própria —
só existe depois que a API tiver subido pelo menos uma vez em algum
ambiente. Não quebra a feature (Mongo funciona sem índice, só faz
collection scan), é só uma pendência de operação a ter em mente.
