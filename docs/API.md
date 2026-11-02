<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# API

As chamadas a `/chat` exigem `Authorization: Bearer <token>`, e o [contrato](https://github.com/Solierrr/ai-geographic/blob/main/openapi.yaml) é exportado por `make openapi`, com a interface `/docs` disponível apenas quando `DOCS_ENABLED` está ligado.

| Grupo | Uso |
|---|---|
| `POST /chat` | Executa um turno e retorna resposta, resultado e especialistas usados |
| `GET /health` e `GET /ready` | Liveness e readiness públicos |
| `POST /debug/chat` | Depuração administrativa fora do contrato público |

O debug exige um administrador autorizado por `DEBUG_ADMIN_SUBS`. Um turno normal de debug grava histórico no serviço de mensagens, sem atualizar fatos de longo prazo. O replay personalizado de um nó não persiste alterações.

```http
POST /chat
Authorization: Bearer <token>
Content-Type: application/json

{"conversation_id":"visita-local","message":"Quais condições devo verificar antes da visita?"}
```

Os erros HTTP seguem o [padrão de erros](https://github.com/Solierrr/docs-warehouse/blob/main/docs/standards/ERRORS.md), mas uma resposta 200 ainda pode trazer `REFUSED`, `DEGRADED` ou `TOOL_FAILED` acompanhado de `reason`, e por isso o cliente precisa avaliar esses campos além do status HTTP.