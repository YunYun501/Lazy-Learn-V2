from abc import ABC, abstractmethod
from typing import AsyncGenerator
from app.models.ai_models import ConceptExtraction, ClassifiedMatch, PracticeProblems


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        model: str,
        stream: bool = False,
        json_mode: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        """Send a chat completion request."""
        ...

    @abstractmethod
    async def extract_concepts(self, user_query: str) -> ConceptExtraction:
        """Step 0: Extract concepts and equation forms from user query."""
        ...

    @abstractmethod
    async def classify_matches(
        self,
        descriptions: list[dict],
        concept: str,
    ) -> list[ClassifiedMatch]:
        """Step 2: Classify whether each description EXPLAINS or USES the concept."""
        ...

    @abstractmethod
    async def generate_explanation(
        self,
        content_chunks: list[str],
        query: str,
        stream: bool = True,
    ) -> str | AsyncGenerator[str, None]:
        """Step 4: Generate a combined explanation from selected content chunks."""
        ...

    @abstractmethod
    async def generate_practice_problems(
        self,
        content: str,
        topic: str,
        count: int = 3,
    ) -> PracticeProblems:
        """Generate practice problems with solutions. Always includes warning disclaimer."""
        ...
