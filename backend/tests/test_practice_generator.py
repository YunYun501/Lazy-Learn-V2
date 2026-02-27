"""Tests for PracticeGenerator — mandatory disclaimer enforcement."""
import json
import pytest
from unittest.mock import MagicMock, AsyncMock

from app.services.practice_generator import (
    PracticeGenerator,
    PRACTICE_DISCLAIMER,
    PRACTICE_SYSTEM_PROMPT,
)


def _make_provider_with_response(problems: list[dict]) -> MagicMock:
    """Create a mock DeepSeekProvider that returns the given problems as JSON."""
    raw = json.dumps({"problems": problems})
    provider = MagicMock()
    provider._call_with_retry = AsyncMock(
        return_value={"choices": [{"message": {"content": raw}}]}
    )
    return provider


async def test_practice_output_always_contains_disclaimer():
    """Every practice response must include the warning disclaimer."""
    problems = [
        {
            "question": "Find the Z-transform of x[n] = 0.5^n u[n].",
            "steps": [
                {
                    "explanation": "Apply the Z-transform definition.",
                    "equation": "X(z) = \\sum_{n=0}^{\\infty} 0.5^n z^{-n}",
                    "theorem_used": "Z-transform definition",
                }
            ],
            "answer": "X(z) = z / (z - 0.5)",
        }
    ]
    provider = _make_provider_with_response(problems)
    generator = PracticeGenerator(deepseek_provider=provider)

    result = await generator.generate_practice(content="", topic="Z-transform")

    assert "warning_disclaimer" in result, "Top-level warning_disclaimer field must be present"
    assert result["warning_disclaimer"] == PRACTICE_DISCLAIMER

    for problem in result["problems"]:
        assert PRACTICE_DISCLAIMER in problem["answer"], (
            "Disclaimer must be embedded in every problem's answer"
        )


async def test_disclaimer_enforced_even_if_ai_omits_it():
    """If AI returns problems without disclaimer, generator must inject it."""
    problems = [
        {
            "question": "Compute the inverse Z-transform.",
            "steps": [],
            "answer": "x[n] = 0.5^n u[n]",  # No disclaimer from AI
        }
    ]
    provider = _make_provider_with_response(problems)
    generator = PracticeGenerator(deepseek_provider=provider)

    result = await generator.generate_practice(content="", topic="Z-transform")

    # Disclaimer must be injected even though AI didn't include it
    assert PRACTICE_DISCLAIMER in result["problems"][0]["answer"]


async def test_practice_system_prompt_requires_theorem_identification():
    """System prompt must instruct AI to identify theorems/equations per step."""
    assert "theorem" in PRACTICE_SYSTEM_PROMPT.lower(), (
        "PRACTICE_SYSTEM_PROMPT must require theorem identification per step"
    )
    assert "step" in PRACTICE_SYSTEM_PROMPT.lower(), (
        "PRACTICE_SYSTEM_PROMPT must require step-by-step solutions"
    )
    assert "latex" in PRACTICE_SYSTEM_PROMPT.lower() or "LaTeX" in PRACTICE_SYSTEM_PROMPT, (
        "PRACTICE_SYSTEM_PROMPT must require LaTeX for math"
    )
