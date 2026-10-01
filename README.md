# ai-geographic

API de um assistente para localizar destinos e sugerir deslocamentos com
dados do Google Maps Platform e previsão do tempo. O fluxo pede origem,
destino, modo ou horário quando necessário, consulta as APIs e só recomenda
uma rota apoiada nos resultados recebidos. Pedidos de catálogo, como listar
pizzarias, ficam fora do escopo.

A primeira versão calcula rotas de carro ou a pé. Pode comparar alternativas
de rota ou três horários dentro de uma janela de até oito horas. A resposta
traz texto e `route_data` com a geometria opcional da rota; a exibição do mapa
no app ou no Google Maps será decidida depois.
Se a geometria for exibida em um mapa, a implementação visual deverá usar
Google Maps e manter as atribuições exigidas pelo provedor.

<p>

[![License](https://img.shields.io/github/license/Solierrr/ai-geographic)](https://github.com/Solierrr/ai-geographic/blob/main/LICENSE)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/Solierrr/ai-geographic)](https://github.com/Solierrr/ai-geographic/commits)
[![GitHub Issues](https://img.shields.io/github/issues/Solierrr/ai-geographic)](https://github.com/Solierrr/ai-geographic/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/Solierrr/ai-geographic)](https://github.com/Solierrr/ai-geographic/pulls)
[![Release](https://img.shields.io/github/v/release/Solierrr/ai-geographic)](https://github.com/Solierrr/ai-geographic/releases)

</p>

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,fastapi,langchain,mongodb,redis,docker" height="48" alt="Stack">
  </a>
</p>

## Aprofunde-se no Projeto!

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [RUNNING.md](./RUNNING.md)
- [docs/plano-implementacao-rotas.md](./docs/plano-implementacao-rotas.md)

## Contribuindo

- Escreva commits em Conventional Commits, em inglês e minúsculas (`feat:`, `fix:` etc.).
- Todo PR deve usar o `.github/pull_request_template.md` deste repositório.
