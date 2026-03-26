import asyncio
import json
import logging
import time
from typing import AsyncGenerator
import httpx
from app.models.ai_models import (
    ConceptExtraction,
    ClassifiedMatch,
    PracticeProblems,
    Problem,
)
from app.services.ai_provider import AIProvider

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
CHAT_MODEL = "deepseek-chat"  # For Steps 0/2: classification (cheap, 8K output)
REASONER_MODEL = "deepseek-reasoner"  # For Step 4: explanations (64K output)

# Constant system prompt prefix for cache hit optimization
# DeepSeek caches based on prefix — keep this IDENTICAL across all calls
SYSTEM_PROMPT_PREFIX = (
    "You are an expert STEM tutor assistant for the Lazy Learn study application. "
    "You help students understand complex technical concepts by analyzing textbook content. "
    "Always be precise, use proper mathematical notation, and cite sources when possible."
)


logger = logging.getLogger(__name__)


class DeepSeekProvider(AIProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = DEEPSEEK_BASE_URL
        self._client: httpx.AsyncClient | None = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                limits=httpx.Limits(
                    max_connections=50,
                    max_keepalive_connections=20,
                ),
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _call_with_retry(
        self,
        payload: dict,
        timeout: float = 60.0,
        max_retries: int = 3,
    ) -> dict:
        """Call DeepSeek API with exponential backoff retry on empty/error responses."""
        delays = [2, 4, 8]
        last_error = None
        model = payload.get("model", "unknown")
        message_count = len(payload.get("messages", []) or [])

        client = self._ensure_client()

        for attempt in range(max_retries):
            t0 = time.perf_counter()
            try:
                logger.debug(
                    "DeepSeek API call started",
                    extra={
                        "model": model,
                        "message_count": message_count,
                        "timeout": timeout,
                    },
                )
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                    timeout=timeout,
                )
                response.raise_for_status()
                data = response.json()

                content = (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                if not content or content.strip() == "":
                    logger.warning(
                        "Empty DeepSeek response content",
                        extra={"model": model, "attempt": attempt + 1},
                    )
                    raise ValueError(
                        f"Empty response from DeepSeek (attempt {attempt + 1})"
                    )

                elapsed_ms = round((time.perf_counter() - t0) * 1000)
                usage = data.get("usage", {})
                logger.info(
                    "DeepSeek API response received",
                    extra={
                        "model": model,
                        "duration_ms": elapsed_ms,
                        "token_usage": usage,
                    },
                )
                return data

            except (ValueError, httpx.HTTPError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = delays[attempt]
                    logger.warning(
                        "DeepSeek API retry",
                        extra={
                            "attempt": attempt + 1,
                            "delay": delay,
                            "error": str(e),
                        },
                    )
                    await asyncio.sleep(delay)

        logger.error(
            "DeepSeek API retries exhausted",
            extra={"error": str(last_error)},
        )
        raise RuntimeError(
            f"DeepSeek API failed after {max_retries} attempts: {last_error}"
        )

    async def chat(
        self,
        messages: list[dict],
        model: str = CHAT_MODEL,
        stream: bool = False,
        json_mode: bool = False,
        temperature: float | None = None,
        timeout: float | None = None,
    ) -> str | AsyncGenerator[str, None]:
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if temperature is not None:
            payload["temperature"] = temperature

        if stream:
            return self._stream_response(payload)
        else:
            data = await self._call_with_retry(payload, timeout=timeout or 60.0)
            return data["choices"][0]["message"]["content"]

    async def _stream_response(self, payload: dict) -> AsyncGenerator[str, None]:
        """Stream response from DeepSeek API with retry logic on errors."""
        delays = [2, 4, 8]
        max_retries = 3
        last_error = None
        model = payload.get("model", "unknown")
        message_count = len(payload.get("messages", []) or [])

        client = self._ensure_client()

        for attempt in range(max_retries):
            try:
                logger.debug(
                    "DeepSeek streaming call started",
                    extra={
                        "model": model,
                        "message_count": message_count,
                        "timeout": 120.0,
                    },
                )
                start_time = time.perf_counter()
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                    timeout=120.0,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                data = json.loads(line[6:])
                                content = (
                                    data.get("choices", [{}])[0]
                                    .get("delta", {})
                                    .get("content", "")
                                )
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                pass
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                logger.info(
                    "DeepSeek streaming response completed",
                    extra={"model": model, "duration_ms": duration_ms},
                )
                return
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = delays[attempt]
                    logger.warning(
                        "DeepSeek streaming retry",
                        extra={
                            "attempt": attempt + 1,
                            "delay": delay,
                            "error": str(e),
                        },
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "DeepSeek streaming retries exhausted",
                        extra={"error": str(last_error)},
                    )
                    raise RuntimeError(
                        f"DeepSeek streaming failed after {max_retries} attempts: {last_error}"
                    )

    async def extract_concepts(self, user_query: str) -> ConceptExtraction:
        """Step 0: Extract concepts and equation forms from user query."""
        messages = [
            {
                "role": "system",
                "content": (
                    f"{SYSTEM_PROMPT_PREFIX}\n\n"
                    "Extract the mathematical concepts and equation forms from the user's query. "
                    "Recognize equation FORMS not just literal text — Y(z) = az/(z-b) is a Z-transform "
                    "regardless of the values of a and b. "
                    'Return JSON: {"concepts": ["concept1", "concept2"], "equations": ["equation form 1"]}'
                ),
            },
            {"role": "user", "content": user_query},
        ]
        payload = {
            "model": CHAT_MODEL,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }
        data = await self._call_with_retry(payload, timeout=60.0)
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return ConceptExtraction(
            concepts=parsed.get("concepts", []),
            equations=parsed.get("equations", []),
        )

    async def classify_matches(
        self,
        descriptions: list[dict],
        concept: str,
    ) -> list[ClassifiedMatch]:
        """Step 2: Classify whether each description EXPLAINS or USES the concept."""
        results = []
        for desc in descriptions:
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"{SYSTEM_PROMPT_PREFIX}\n\n"
                        "Classify whether this chapter EXPLAINS or USES the given concept. "
                        "EXPLAINS = introduces, derives, defines, proves the concept. "
                        "USES = applies the concept in examples, problems, or design without explaining it. "
                        'Return JSON: {"classification": "EXPLAINS|USES", "confidence": 0.0-1.0, "reason": "..."}'
                    ),
                },
                {
                    "role": "user",
                    "content": f"Concept: {concept}\n\nChapter description:\n{desc.get('content', '')}",
                },
            ]
            payload = {
                "model": CHAT_MODEL,
                "messages": messages,
                "response_format": {"type": "json_object"},
            }
            data = await self._call_with_retry(payload, timeout=60.0)
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            results.append(
                ClassifiedMatch(
                    source=desc.get("source", ""),
                    chapter=desc.get("chapter", ""),
                    subchapter=desc.get("subchapter", ""),
                    classification=parsed.get("classification", "USES"),
                    confidence=parsed.get("confidence", 0.5),
                    reason=parsed.get("reason", ""),
                )
            )
        return results

    async def generate_explanation(
        self,
        content_chunks: list[str],
        query: str,
        stream: bool = True,
    ) -> str | AsyncGenerator[str, None]:
        """Step 4: Generate explanation using deepseek-reasoner for 64K output."""
        combined_content = "\n\n---\n\n".join(content_chunks)
        messages = [
            {
                "role": "system",
                "content": (
                    f"{SYSTEM_PROMPT_PREFIX}\n\n"
                    "Generate a comprehensive explanation based on the provided textbook content. "
                    "Use LaTeX for all mathematical expressions (inline: \\( \\), block: \\[ \\]). "
                    "Structure your response with clear sections. "
                    "Always cite which textbook/chapter the information comes from."
                ),
            },
            {
                "role": "user",
                "content": f"Query: {query}\n\nTextbook content:\n{combined_content}",
            },
        ]
        payload = {
            "model": REASONER_MODEL,
            "messages": messages,
            "stream": stream,
        }
        if stream:
            return self._stream_response(payload)
        else:
            data = await self._call_with_retry(payload, timeout=120.0)
            return data["choices"][0]["message"]["content"]

    async def generate_practice_problems(
        self,
        content: str,
        topic: str,
        count: int = 3,
    ) -> PracticeProblems:
        """Generate practice problems. WARNING DISCLAIMER is always included."""
        messages = [
            {
                "role": "system",
                "content": (
                    f"{SYSTEM_PROMPT_PREFIX}\n\n"
                    f"Generate {count} practice problems about the given topic based on the textbook content. "
                    "Use LaTeX for all mathematical expressions. "
                    'Return JSON: {"problems": [{"question": "...", "solution": "..."}]}'
                ),
            },
            {
                "role": "user",
                "content": f"Topic: {topic}\n\nContent:\n{content}",
            },
        ]
        payload = {
            "model": CHAT_MODEL,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }
        data = await self._call_with_retry(payload, timeout=60.0)
        content_str = data["choices"][0]["message"]["content"]
        parsed = json.loads(content_str)
        problems = [
            Problem(
                question=p["question"],
                solution=p["solution"],
                # warning_disclaimer is always set by the model default
            )
            for p in parsed.get("problems", [])
        ]
        return PracticeProblems(topic=topic, problems=problems)
