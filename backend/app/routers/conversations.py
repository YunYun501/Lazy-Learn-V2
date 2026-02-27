"""FastAPI router for conversation history and follow-up handling."""
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.config import settings
from app.services.deepseek_provider import DeepSeekProvider
from app.services.storage import MetadataStore
from app.services.conversation import ConversationHandler

router = APIRouter(prefix="/api", tags=["conversations"])


def _get_handler() -> ConversationHandler:
    provider = DeepSeekProvider(api_key=settings.DEEPSEEK_API_KEY)
    store = MetadataStore(db_path=Path(settings.DATA_DIR) / "lazy_learn.db")
    return ConversationHandler(deepseek_provider=provider, store=store)


class FollowupRequest(BaseModel):
    conversation_id: str
    message: str


async def _sse_followup(conversation_id: str, message: str) -> AsyncGenerator[str, None]:
    handler = _get_handler()
    async for chunk in handler.handle_followup(conversation_id, message):
        yield f"data: {chunk}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/conversations/followup")
async def followup(request: FollowupRequest) -> StreamingResponse:
    """Stream a follow-up response that maintains conversation context."""
    return StreamingResponse(
        _sse_followup(request.conversation_id, request.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str) -> list[dict]:
    """Retrieve all messages for a conversation in chronological order."""
    handler = _get_handler()
    return await handler.get_messages(conversation_id)
