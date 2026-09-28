from typing import Final

MAX_SPECIALISTS_PER_REQUEST: Final[int] = 3

# Cada rota aqui precisa ter um node registrado em
# `src/workflow/graph/graph.py` e ser conhecida pelo prompt do roteador em
# `src/agents/specialist/router/router_prompt.py`.
SPECIALIST_ROUTES: Final[frozenset[str]] = frozenset(
    {
        "example_specialist",
        "example_specialist_two",
    }
)
