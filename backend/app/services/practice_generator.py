"""Practice question + solution generator with mandatory warning disclaimer.

Uses deepseek-reasoner for detailed, step-by-step worked solutions with
LaTeX equations and theorem identification.
"""
import json
from typing import AsyncGenerator

from app.services.deepseek_provider import DeepSeekProvider, REASONER_MODEL

# Mandatory disclaimer — ALWAYS appended to every practice response
PRACTICE_DISCLAIMER = (
    "⚠️ **Warning**: AI-generated solutions may contain calculation errors. "
    "Verify your answers independently or cross-check with your textbook."
)

# Constant system prompt for DeepSeek cache hit optimization
PRACTICE_SYSTEM_PROMPT = (
    "You are an expert STEM tutor assistant for the Lazy Learn study application. "
    "You help students understand complex technical concepts by analyzing textbook content. "
    "Always be precise, use proper mathematical notation, and cite sources when possible.\n\n"
    "Generate practice problems with detailed step-by-step solutions. "
    "For each problem:\n"
    "1) State the problem clearly with all given values.\n"
    "2) Provide step-by-step solution with LaTeX equations.\n"
    "3) Identify which equation/theorem is used in each step "
    "(e.g., 'Applying the Z-transform definition').\n"
    "4) Include a clearly boxed final answer.\n"
    "Use LaTeX for ALL math: inline $...$ and display $$...$$.\n\n"
    "Return JSON with this exact structure:\n"
    '{"problems": [{"question": "...", "steps": [{"explanation": "...", '
    '"equation": "...", "theorem_used": "..."}], "answer": "..."}]}'
)


class PracticeGenerator:
    """Generates practice problems with mandatory warning disclaimers."""

    def __init__(self, deepseek_provider: DeepSeekProvider):
        self.provider = deepseek_provider

    def _enforce_disclaimer(self, problems: list[dict]) -> list[dict]:
        """Ensure every problem has the warning disclaimer in its answer field."""
        for problem in problems:
            answer = problem.get("answer", "")
            if PRACTICE_DISCLAIMER not in answer:
                problem["answer"] = answer + f"\n\n{PRACTICE_DISCLAIMER}"
        return problems

    async def generate_practice(
        self,
        content: str,
        topic: str,
        difficulty: str = "medium",
        count: int = 3,
    ) -> dict:
        """Generate practice problems with step-by-step solutions.

        Returns a dict with:
          - problems: list of problem dicts (question, steps, answer)
          - warning_disclaimer: always present
        """
        messages = [
            {"role": "system", "content": PRACTICE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Generate {count} practice problems about '{topic}' "
                    f"at {difficulty} difficulty level.\n\n"
                    f"Textbook content:\n{content}"
                ),
            },
        ]

        payload = {
            "model": REASONER_MODEL,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }

        data = await self.provider._call_with_retry(payload, timeout=120.0)
        raw = data["choices"][0]["message"]["content"]

        # Strip markdown fences if present
        if raw.strip().startswith("```"):
            lines = raw.strip().splitlines()
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        parsed = json.loads(raw)
        problems = parsed.get("problems", [])

        # HARD REQUIREMENT: disclaimer must be present in every problem
        problems = self._enforce_disclaimer(problems)

        return {
            "topic": topic,
            "difficulty": difficulty,
            "problems": problems,
            "warning_disclaimer": PRACTICE_DISCLAIMER,
        }
