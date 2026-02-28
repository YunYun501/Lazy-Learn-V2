"""Conversational follow-up handler with SQLite-backed history.

Manages conversation context so follow-up questions (e.g., 'give me more examples',
'explain step 3 differently') reference the previous explanation without the user
having to repeat themselves.
"""
import uuid
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

from app.services.deepseek_provider import DeepSeekProvider, REASONER_MODEL
from app.services.storage import MetadataStore

# Constant system prompt for cache hit optimization
CONVERSATION_SYSTEM_PROMPT = (
    "You are an expert STEM tutor assistant for the Lazy Learn study application. "
    "You help students understand complex technical concepts by analyzing textbook content. "
    "Always be precise, use proper mathematical notation, and cite sources when possible.\n\n"
    "You are continuing a tutoring conversation. The student may ask follow-up questions "
    "about the topic already discussed. Maintain context from the conversation history. "
    "Use LaTeX for ALL equations: inline $...$ and display $$...$$. "
    "Be thorough but clear."
)


class ConversationHandler:
    """Manages conversation history and routes follow-up questions."""

    def __init__(self, deepseek_provider: DeepSeekProvider, store: MetadataStore):
        self.provider = deepseek_provider
        self.store = store

    async def create_conversation(self, query: str, course_id: str | None = None) -> str:
        """Create a new conversation record and return its ID."""
        conversation_id = str(uuid.uuid4())
        await self.store.create_conversation(
            conversation_id=conversation_id,
            query=query,
            course_id=course_id,
        )
        return conversation_id

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> None:
        """Append a message to the conversation history."""
        await self.store.add_message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )

    async def get_messages(self, conversation_id: str) -> list[dict]:
        """Retrieve all messages for a conversation."""
        return await self.store.get_messages(conversation_id)

    async def handle_followup(
        self,
        conversation_id: str,
        message: str,
    ) -> AsyncGenerator[str, None]:
        """Stream a follow-up response that maintains conversation context.

        Loads the full conversation history from SQLite and sends it to
        DeepSeek so the AI has context of what was already discussed.
        """
        # Load history
        history = await self.get_messages(conversation_id)

        # Auto-create conversation record if it doesn't exist yet
        if not history:
            await self.store.create_conversation(
                conversation_id=conversation_id,
                query=message,
            )
        # Build messages list: system + history + new user message
        messages = [{"role": "system", "content": CONVERSATION_SYSTEM_PROMPT}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": message})

        payload = {
            "model": REASONER_MODEL,
            "messages": messages,
            "stream": True,
        }

        # Save user message before streaming
        await self.add_message(conversation_id, "user", message)

        # Stream response and collect for saving
        full_response = []
        async for chunk in self.provider._stream_response(payload):
            full_response.append(chunk)
            yield chunk

        # Save assistant response to history
        if full_response:
            await self.add_message(conversation_id, "assistant", "".join(full_response))
