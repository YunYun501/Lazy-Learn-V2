from app.services.ai_provider import AIProvider
from app.services.deepseek_provider import DeepSeekProvider
from app.services.openai_provider import OpenAIProvider
from app.models.ai_models import ConceptExtraction, ClassifiedMatch, PracticeProblems

class AIRouter:
    """
    Smart router that selects the appropriate AI provider per task type.
    - Text tasks (concept extraction, classification, explanation): DeepSeek (cheaper)
    - Vision tasks (image analysis): OpenAI GPT-4o (if available)
    """

    def __init__(self, deepseek_api_key: str, openai_api_key: str = ""):
        self.deepseek = DeepSeekProvider(api_key=deepseek_api_key)
        self.openai = OpenAIProvider(api_key=openai_api_key)

    @property
    def vision_available(self) -> bool:
        """True if OpenAI vision is configured."""
        return self.openai.available

    async def extract_concepts(self, user_query: str) -> ConceptExtraction:
        """Always uses DeepSeek."""
        return await self.deepseek.extract_concepts(user_query)

    async def classify_matches(self, descriptions, concept: str) -> list[ClassifiedMatch]:
        """Always uses DeepSeek."""
        return await self.deepseek.classify_matches(descriptions, concept)

    async def generate_explanation(self, content_chunks, query: str, stream: bool = True):
        """Always uses DeepSeek (deepseek-reasoner for 64K output)."""
        return await self.deepseek.generate_explanation(content_chunks, query, stream)

    async def generate_practice_problems(self, content: str, topic: str, count: int = 3) -> PracticeProblems:
        """Always uses DeepSeek."""
        return await self.deepseek.generate_practice_problems(content, topic, count)

    async def analyze_image(self, image_path: str, prompt: str) -> str:
        """
        Uses OpenAI GPT-4o Vision if available.
        Falls back to 'Vision not available' message if not configured.
        """
        return await self.openai.analyze_image(image_path, prompt)
