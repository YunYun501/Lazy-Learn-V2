"""FastAPI router for practice question generation."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.services.deepseek_provider import DeepSeekProvider
from app.services.practice_generator import PracticeGenerator

router = APIRouter(prefix="/api", tags=["practice"])


class PracticeRequest(BaseModel):
    topic: str
    content: str = ""
    difficulty: str = "medium"  # easy | medium | hard
    count: int = 3


@router.post("/practice")
async def generate_practice(request: PracticeRequest) -> dict:
    """Generate practice problems with step-by-step solutions and mandatory warning.

    Returns JSON with:
      - problems: list of {question, steps, answer} (answer always contains disclaimer)
      - warning_disclaimer: always present
    """
    provider = DeepSeekProvider(api_key=settings.DEEPSEEK_API_KEY)
    generator = PracticeGenerator(deepseek_provider=provider)

    return await generator.generate_practice(
        content=request.content,
        topic=request.topic,
        difficulty=request.difficulty,
        count=request.count,
    )
