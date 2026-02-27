"""Tests for ConversationHandler — context-aware follow-up handling."""
import pytest
from unittest.mock import MagicMock, AsyncMock

from app.services.conversation import ConversationHandler, CONVERSATION_SYSTEM_PROMPT


def _make_store(messages: list[dict] | None = None) -> MagicMock:
    """Create a mock MetadataStore."""
    store = MagicMock()
    store.create_conversation = AsyncMock(return_value="conv-123")
    store.add_message = AsyncMock(return_value="msg-456")
    store.get_messages = AsyncMock(return_value=messages or [])
    return store


async def test_followup_includes_conversation_history_in_prompt():
    """handle_followup() must include prior messages in the AI payload."""
    prior_messages = [
        {"role": "user", "content": "Explain the Z-transform."},
        {"role": "assistant", "content": "The Z-transform is defined as..."},
    ]
    store = _make_store(messages=prior_messages)

    captured_payload = {}

    async def mock_stream(payload):
        captured_payload.update(payload)
        yield "follow-up response"

    provider = MagicMock()
    provider._stream_response = mock_stream

    handler = ConversationHandler(deepseek_provider=provider, store=store)

    chunks = []
    async for chunk in handler.handle_followup("conv-123", "Give me an example."):
        chunks.append(chunk)

    # The payload messages must include the prior history
    sent_messages = captured_payload.get("messages", [])
    roles = [m["role"] for m in sent_messages]

    assert "system" in roles, "System prompt must be included"
    assert "user" in roles, "Prior user messages must be included"
    assert "assistant" in roles, "Prior assistant messages must be included"

    # The new follow-up message must be the last user message
    user_messages = [m["content"] for m in sent_messages if m["role"] == "user"]
    assert "Give me an example." in user_messages[-1]


async def test_followup_saves_messages_to_history():
    """handle_followup() must save both the user message and AI response."""
    store = _make_store()

    async def mock_stream(payload):
        yield "chunk1"
        yield "chunk2"

    provider = MagicMock()
    provider._stream_response = mock_stream

    handler = ConversationHandler(deepseek_provider=provider, store=store)

    chunks = []
    async for chunk in handler.handle_followup("conv-123", "What is the ROC?"):
        chunks.append(chunk)

    # add_message should be called twice: user + assistant
    assert store.add_message.call_count == 2

    calls = store.add_message.call_args_list
    roles_saved = [call.kwargs.get("role") or call.args[1] for call in calls]
    assert "user" in roles_saved
    assert "assistant" in roles_saved


async def test_conversation_system_prompt_maintains_context():
    """System prompt must instruct AI to maintain conversation context."""
    assert "context" in CONVERSATION_SYSTEM_PROMPT.lower() or "history" in CONVERSATION_SYSTEM_PROMPT.lower(), (
        "CONVERSATION_SYSTEM_PROMPT must reference conversation context/history"
    )
    assert "follow" in CONVERSATION_SYSTEM_PROMPT.lower() or "continuing" in CONVERSATION_SYSTEM_PROMPT.lower(), (
        "CONVERSATION_SYSTEM_PROMPT must indicate this is a continuing conversation"
    )
