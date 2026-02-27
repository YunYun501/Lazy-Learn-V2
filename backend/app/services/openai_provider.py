import base64
import json
from pathlib import Path
from typing import AsyncGenerator
import httpx

from app.services.ai_provider import AIProvider
from app.models.ai_models import ConceptExtraction, ClassifiedMatch, PracticeProblems, Problem

OPENAI_BASE_URL = "https://api.openai.com/v1"
VISION_MODEL = "gpt-4o"
TEXT_MODEL = "gpt-4o-mini"  # Cheaper for text tasks

class OpenAIProvider(AIProvider):
    """
    Optional OpenAI provider for vision tasks.
    Falls back gracefully when API key is not configured.
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.available = bool(api_key and api_key.strip())

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def analyze_image(self, image_path: str, prompt: str) -> str:
        """
        Analyze an image using GPT-4o Vision.
        Returns 'Vision not available' if OpenAI key not configured.
        """
        if not self.available:
            return "Vision analysis not available. Configure OPENAI_API_KEY to enable."

        # Read and encode image
        image_data = Path(image_path).read_bytes()
        b64_image = base64.b64encode(image_data).decode("utf-8")

        # Determine image type
        ext = Path(image_path).suffix.lower()
        media_type = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }.get(ext, "image/png")

        payload = {
            "model": VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{b64_image}",
                                "detail": "high",
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "max_tokens": 1000,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def chat(self, messages, model=TEXT_MODEL, stream=False, json_mode=False):
        """Text chat via OpenAI. Falls back gracefully if not available."""
        if not self.available:
            raise RuntimeError("OpenAI API key not configured")

        payload = {"model": model, "messages": messages, "stream": stream}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def extract_concepts(self, user_query: str) -> ConceptExtraction:
        """Delegate to DeepSeek — OpenAI not used for text tasks."""
        raise NotImplementedError("Use DeepSeek for concept extraction")

    async def classify_matches(self, descriptions, concept):
        """Delegate to DeepSeek — OpenAI not used for text tasks."""
        raise NotImplementedError("Use DeepSeek for classification")

    async def generate_explanation(self, content_chunks, query, stream=True):
        """Delegate to DeepSeek — OpenAI not used for explanations."""
        raise NotImplementedError("Use DeepSeek for explanations")

    async def generate_practice_problems(self, content, topic, count=3):
        """Delegate to DeepSeek — OpenAI not used for practice problems."""
        raise NotImplementedError("Use DeepSeek for practice problems")
