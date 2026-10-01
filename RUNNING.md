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
- **Google Maps Platform**, habilitar Places API (New), Routes API, Time Zone API e Weather API na conta Google Cloud, com faturamento/quotas adequados, e preencher `GOOGLE_MAPS_API_KEY` no `.env`. A chave `GOOGLE_API_KEY` é do modelo Gemini.

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

## Contrato de deslocamento

Envie `POST /chat` com Bearer JWT, `conversation_id` e `message`. O app pode
enviar `current_location` somente após permissão da pessoa e deve reenviar as
coordenadas em cada mensagem que dependa de “aqui”, inclusive depois de uma
pergunta de esclarecimento. Envie `user_timezone` (fuso IANA) para interpretar
“hoje” e “amanhã” no local do usuário; sem ele, vale `DEFAULT_TIMEZONE`.

```json
{
  "conversation_id": "viagem-123",
  "message": "Como vou daqui ao Parque Ibirapuera de carro agora?",
  "current_location": {"latitude": -23.5505, "longitude": -46.6333},
  "user_timezone": "America/Sao_Paulo"
}
```

A resposta contém `response`, `specialists_used`, `workflow_steps` e
`route_data` quando uma recomendação de rota foi aprovada. O contrato completo
está em `openapi.yaml`. Sem credenciais externas, use os testes automatizados
com respostas simuladas; as integrações reais requerem a conta configurada.
