# Rodando o Projeto Localmente

Este repositório é Python. O processo local é sempre o mesmo: clonar, criar um ambiente virtual, instalar as dependências do `requirements.txt` (ou `.lock`) e subir a aplicação via `uvicorn`. Antes de iniciar, verifique a seção de impedimentos abaixo — alguns repositórios dependem de credenciais externas mesmo em ambiente local.

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,fastapi,pydantic,github,gcp" height="48" alt="Rodando o Projeto — Python">
  </a>
</p>

## Possíveis Impedimentos

- **Python 3.12+ instalado localmente**, a mesma versão usada no `Dockerfile` (`python:latest`) — rodar fora do container exige essa versão instalada na máquina.
- **Acesso ao Google Cloud (`gcloud auth login`)**, serviços que integram com GCP em runtime (Storage, Pub/Sub, Vertex AI) precisam de credenciais válidas localmente, já que em produção isso vem do manifesto do [Infra-gitops](https://github.com/Solierrr/infra-gitops).
- **Secrets locais**, variáveis de ambiente equivalentes às injetadas em runtime pelo [Infisical](https://infisical.com) (chaves de API de LLM, strings de conexão de banco) precisam ser criadas manualmente em um `.env` local — sem elas, a aplicação sobe mas falha ao tentar se conectar em dependências externas.

## Instalação do Projeto

### Iniciando o repositório com o Github

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=github,vscode" height="48" alt="Frameworks">
  </a>
</p>

Clone o repositório e abra no VS Code.

```Comandos para clonar o repositório
git clone https://github.com/Solierrr/ai-geographic.git
cd ./ai-geographic
code . -r
```

### Instalando dependências necessárias para rodar o projeto localmente

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python" height="48" alt="Frameworks">
  </a>
</p>

Crie um ambiente virtual antes de instalar as dependências, para não poluir o Python global da máquina. O comando de start varia conforme o entrypoint do repositório — ajuste o módulo (`main:app`, `app.main:app`, etc.) conforme o `CMD`/`ENTRYPOINT` do `Dockerfile` do projeto.

```Comandos para instalação de dependências
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.api.app:app --reload
```

## Autenticação local

O JWT de usuário vem do `api-auth` de verdade, sem emissor falso: suba a stack local com `make dev-up` no `database-console` e aponte `JWT_JWKS_URL` para o JWKS dele (`http://localhost:8081/.well-known/jwks.json`). Para conversar pelo terminal, rode `python main.py` e informe o access token obtido no login do `api-auth` local.

## Telemetria (OpenTelemetry)

A telemetria é ligada pelo próprio código, em `setup_observability` (`src/core/observability/observability.py`), chamada em `src/api/app.py`. Não há wrapper nem `opentelemetry-instrument`. A app envia traces, métricas e logs por OTLP/HTTP para `OTEL_EXPORTER_OTLP_ENDPOINT` (padrão `http://localhost:4318`). Ficam instrumentados as requisições HTTP de entrada, as chamadas httpx, o Mongo (pymongo) e o Redis.

- O nome do serviço é fixo no código (`ai-geographic`); não existe `OTEL_SERVICE_NAME`.
- `/health` não gera span nem métrica.
- Toda resposta traz o header `X-Trace-Id`, e os erros trazem `traceId` no corpo.
- Para desligar (por exemplo, em testes), use `OTEL_SDK_DISABLED=true`. Sem isso, a telemetria fica ligada.

Para ver a telemetria localmente, suba o Grafana local com `make obs-up` no repositório `infra-otel-collector` (ver `docs-warehouse/helps/TRY-LOCAL.md`).

```text
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
SERVICE_VERSION=dev
DEPLOYMENT_ENVIRONMENT=local
OTEL_TRACES_SAMPLING_PROBABILITY=1.0
# OTEL_SDK_DISABLED=true
```

## Autenticação e CORS do `/chat`

O `POST /chat` valida o JWT do `api-auth` (RS256 via `JWT_JWKS_URL`, emissor `JWT_ISSUER`) antes de rodar o turno: token inválido, expirado ou de refresh responde `401`. Fora do ambiente `LOCAL`, sem `JWT_JWKS_URL` a rota responde `503` em vez de ficar aberta. As origens do navegador autorizadas vêm de `CORS_ALLOWED_ORIGINS` (lista separada por vírgula, sem credenciais e sem `*`).
