from datetime import datetime

from src.infra.database.mongo.schemas.conversation_schema import (
    ConversationSchema,
)
from src.infra.database.mongo.schemas.message_schema import MessageSchema


def test_conversation_schema_accepts_expected_fields():
    started_at = datetime(2026, 7, 1, 10, 0, 0)
    last_interaction_at = datetime(2026, 7, 1, 10, 5, 0)

    conversation = ConversationSchema(
        conversation_id="conv-1",
        user_id=123,
        user_type="lead",
        active_agent="orchestrator",
        status="active",
        started_at=started_at,
        last_interaction_at=last_interaction_at,
    )

    assert conversation.conversation_id == "conv-1"
    assert conversation.user_id == 123
    assert conversation.user_type == "lead"
    assert conversation.user_details == {}
    assert conversation.active_agent == "orchestrator"
    assert conversation.status == "active"
    assert conversation.started_at == started_at
    assert conversation.last_interaction_at == last_interaction_at


def test_conversation_schema_accepts_user_details():
    conversation = ConversationSchema(
        conversation_id="conv-1",
        user_id=123,
        user_type="supplier",
        user_details={"company": "ExemploCorp"},
        active_agent="orchestrator",
        status="active",
        started_at=datetime(2026, 7, 1, 10, 0, 0),
        last_interaction_at=datetime(2026, 7, 1, 10, 5, 0),
    )

    assert conversation.user_details == {"company": "ExemploCorp"}


def test_message_schema_defaults_optional_fields():
    timestamp = datetime(2026, 7, 1, 10, 0, 0)

    message = MessageSchema(
        conversation_id="conv-1",
        role="user",
        content="quero um sistema solar",
        timestamp=timestamp,
    )

    assert message.agent is None
    assert message.metadata == {}


def test_message_schema_accepts_agent_and_metadata():
    timestamp = datetime(2026, 7, 1, 10, 0, 0)

    message = MessageSchema(
        conversation_id="conv-1",
        role="assistant",
        content="posso ajudar",
        agent="orchestrator",
        timestamp=timestamp,
        metadata={"source": "workflow"},
    )

    assert message.agent == "orchestrator"
    assert message.metadata == {"source": "workflow"}
