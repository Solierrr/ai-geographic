from src.core.llm.llm_chain import llm_chain

MEMORY_EXTRACTION_PROMPT = """Você mantém um perfil de fatos duráveis sobre um \
usuário do Solaria Campo, com base no histórico de conversas.

Fatos existentes:
{fatos_existentes}

Última troca da conversa:
{ultima_troca}

Devolva a lista atualizada de fatos, um por linha, sem numeração nem marcador. \
Mantenha os válidos, adicione fatos duráveis novos (papel do usuário na \
plataforma, preferências, contexto relevante), remova os contraditos. \
Nunca inclua dado sensível (documento, valor financeiro, senha, pagamento). \
Máximo de 20 linhas."""


async def extrair_fatos_atualizados(
    fatos_existentes: list[str], ultima_troca: str
) -> list[str]:
    llm = llm_chain()
    resposta = await llm.ainvoke(
        MEMORY_EXTRACTION_PROMPT.format(
            fatos_existentes="\n".join(fatos_existentes) or "(nenhum ainda)",
            ultima_troca=ultima_troca,
        )
    )
    linhas = [linha.strip() for linha in resposta.content.splitlines()]
    return [linha for linha in linhas if linha][:20]
