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
