from ai_lib.observability import StepTracker as _StepTracker

from src.infra.api_messenger.client import enviar_observabilidade


class StepTracker(_StepTracker):
    def __init__(self, conversation_id: str):
        super().__init__(conversation_id, enviar_observabilidade)
