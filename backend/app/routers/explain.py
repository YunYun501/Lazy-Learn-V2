"""FastAPI router for Step 4: streaming AI explanation endpoint."""
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.config import settings
from app.services.deepseek_provider import DeepSeekProvider
from app.services.explanation_generator import ExplanationGenerator, SelectedChapter

router = APIRouter(prefix="/api", tags=["explain"])


class ChapterRef(BaseModel):
    textbook_id: str
    chapter_num: str
    classification: str = "EXPLAINS"
    textbook_title: str = ""


class ExplainRequest(BaseModel):
    chapters: list[ChapterRef]
    query: str


async def _sse_generator(
    chapters: list[ChapterRef],
    query: str,
) -> AsyncGenerator[str, None]:
    """Wrap ExplanationGenerator output as SSE events."""
    provider = DeepSeekProvider(api_key=settings.DEEPSEEK_API_KEY)
    data_dir = Path(settings.DATA_DIR)
    generator = ExplanationGenerator(deepseek_provider=provider, data_dir=data_dir)

    selected = [
        SelectedChapter(
            textbook_id=ch.textbook_id,
            chapter_num=ch.chapter_num,
            classification=ch.classification,
            textbook_title=ch.textbook_title,
        )
        for ch in chapters
    ]

    async for chunk in generator.generate_explanation(selected, query):
        yield f"data: {chunk}\n\n"

    # Signal stream end
    yield "data: [DONE]\n\n"


@router.post("/explain")
async def explain(request: ExplainRequest) -> StreamingResponse:
    """Stream an AI explanation for the selected textbook chapters.

    Returns Server-Sent Events (SSE) with each chunk as:
        data: <chunk text>\\n\\n

    The stream ends with:
        data: [DONE]\\n\\n
    """
    return StreamingResponse(
        _sse_generator(request.chapters, request.query),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
