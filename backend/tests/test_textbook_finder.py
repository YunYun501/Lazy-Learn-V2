"""Tests for the Textbook Finder service (Task 26)."""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.textbook_finder import (
    PIRACY_DOMAINS,
    SAFE_FALLBACK_URL,
    TEXTBOOK_FINDER_SYSTEM_PROMPT,
    TextbookRecommendation,
    _is_piracy_url,
    _sanitise_recommendations,
    find_textbooks,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_recommendation(
    title: str = "Signals and Systems",
    author: str = "Oppenheim & Willsky",
    isbn: str = "978-0138147570",
    relevance_reason: str = "Classic text for signal processing courses.",
    legal_source_url: str = "https://www.pearson.com/",
    source_type: str = "publisher",
) -> dict:
    return {
        "title": title,
        "author": author,
        "isbn": isbn,
        "relevance_reason": relevance_reason,
        "legal_source_url": legal_source_url,
        "source_type": source_type,
    }


def _make_ai_json(recs: list[dict]) -> str:
    """Return a JSON-encoded array of recommendations as the AI would produce."""
    return json.dumps(recs)


def _make_provider(return_value: str) -> MagicMock:
    provider = MagicMock()
    provider.chat = AsyncMock(return_value=return_value)
    return provider


# ---------------------------------------------------------------------------
# Test 1: Recommendations include required fields (title, author, legal_source_url)
# ---------------------------------------------------------------------------


async def test_recommendations_have_required_fields():
    """find_textbooks() must return TextbookRecommendation objects with all required fields."""
    recs = [
        _make_recommendation(
            title="Modern Control Engineering",
            author="Katsuhiko Ogata",
            legal_source_url="https://www.pearson.com/store/p/modern-control-engineering/",
            source_type="publisher",
        ),
        _make_recommendation(
            title="University Physics",
            author="Young & Freedman",
            legal_source_url="https://openstax.org/subjects/science",
            source_type="open_access",
        ),
    ]
    provider = _make_provider(_make_ai_json(recs))

    results = await find_textbooks(
        course_descriptions=["Introduction to feedback control systems and transfer functions."],
        provider=provider,
    )

    assert len(results) == 2
    for rec in results:
        assert isinstance(rec, TextbookRecommendation)
        assert rec.title, "title must not be empty"
        assert rec.author, "author must not be empty"
        assert rec.legal_source_url.startswith("http"), "legal_source_url must be a URL"

    assert results[0].title == "Modern Control Engineering"
    assert results[1].source_type == "open_access"


# ---------------------------------------------------------------------------
# Test 2: Piracy URLs are replaced with the safe fallback
# ---------------------------------------------------------------------------


async def test_piracy_urls_are_replaced():
    """Any recommendation with a piracy URL must have it replaced by the safe fallback."""
    recs = [
        _make_recommendation(
            title="Stolen Textbook",
            legal_source_url="https://libgen.rs/book/index.php?md5=abc123",
        ),
        _make_recommendation(
            title="Another Pirated Book",
            legal_source_url="https://z-lib.org/book/12345",
        ),
        _make_recommendation(
            title="Legal Textbook",
            legal_source_url="https://openstax.org/details/books/university-physics",
        ),
    ]
    provider = _make_provider(_make_ai_json(recs))

    results = await find_textbooks(
        course_descriptions=["Some course material."],
        provider=provider,
    )

    assert len(results) == 3
    # First two had piracy URLs → replaced
    assert results[0].legal_source_url == SAFE_FALLBACK_URL, (
        f"Expected fallback URL, got: {results[0].legal_source_url}"
    )
    assert results[1].legal_source_url == SAFE_FALLBACK_URL, (
        f"Expected fallback URL, got: {results[1].legal_source_url}"
    )
    # Third had a legal URL → unchanged
    assert "openstax.org" in results[2].legal_source_url


# ---------------------------------------------------------------------------
# Test 3: Course topic correctly inferred from control systems descriptions
# ---------------------------------------------------------------------------


async def test_control_systems_topic_inferred():
    """For control-systems descriptions, returned textbooks must be relevant to that domain."""
    control_recs = [
        _make_recommendation(
            title="Modern Control Engineering",
            author="Katsuhiko Ogata",
            isbn="978-0136156734",
            relevance_reason="Covers PID controllers, state-space models, and stability analysis.",
            legal_source_url="https://www.pearson.com/",
            source_type="publisher",
        ),
        _make_recommendation(
            title="Feedback Control of Dynamic Systems",
            author="Franklin, Powell & Emami-Naeini",
            isbn="978-0133496598",
            relevance_reason="Comprehensive treatment of control system design and analysis.",
            legal_source_url="https://www.pearson.com/store/p/feedback-control-of-dynamic-systems/",
            source_type="publisher",
        ),
        _make_recommendation(
            title="Control Systems Engineering",
            author="Norman Nise",
            isbn="978-1119474227",
            relevance_reason="Industry-standard text for undergraduate control courses.",
            legal_source_url="https://www.wiley.com/",
            source_type="publisher",
        ),
    ]
    provider = _make_provider(_make_ai_json(control_recs))

    descriptions = [
        "Chapter 4: PID Controller Design. Covers proportional, integral, and derivative "
        "control actions, Ziegler-Nichols tuning, and closed-loop stability analysis.",
        "Chapter 7: State-Space Representation. Introduces state variables, controllability, "
        "observability, and the transition matrix for linear time-invariant systems.",
    ]

    results = await find_textbooks(course_descriptions=descriptions, provider=provider)

    assert len(results) == 3

    # The prompt sent to DeepSeek should contain the descriptions
    call_args = provider.chat.call_args
    messages = call_args[1]["messages"] if call_args[1] else call_args[0][0]
    user_message = next(m["content"] for m in messages if m["role"] == "user")
    assert "PID" in user_message or "State-Space" in user_message, (
        "User message must contain course description content"
    )

    # All results should be control-related by the mock data
    titles = [r.title for r in results]
    assert "Modern Control Engineering" in titles
    assert "Feedback Control of Dynamic Systems" in titles


# ---------------------------------------------------------------------------
# Test 4: Markdown-fenced JSON is parsed correctly
# ---------------------------------------------------------------------------


async def test_markdown_fenced_json_is_handled():
    """AI responses wrapped in ```json fences must be parsed without errors."""
    recs = [_make_recommendation(title="OpenStax Calculus")]
    fenced_response = f"```json\n{json.dumps(recs)}\n```"
    provider = _make_provider(fenced_response)

    results = await find_textbooks(
        course_descriptions=["Calculus course material."],
        provider=provider,
    )

    assert len(results) == 1
    assert results[0].title == "OpenStax Calculus"


# ---------------------------------------------------------------------------
# Test 5: _is_piracy_url helper correctly identifies piracy domains
# ---------------------------------------------------------------------------


def test_is_piracy_url_detects_all_blocked_domains():
    """_is_piracy_url must return True for every domain in PIRACY_DOMAINS."""
    for domain in PIRACY_DOMAINS:
        assert _is_piracy_url(f"https://{domain}.com/somebook"), (
            f"Expected {domain} to be detected as piracy"
        )

    # Legal sites must pass
    assert not _is_piracy_url("https://openstax.org/details/books/algebra")
    assert not _is_piracy_url("https://books.google.com/books?id=abc")
    assert not _is_piracy_url("https://ocw.mit.edu/courses/")
    assert not _is_piracy_url("https://www.springer.com/book/123")


# ---------------------------------------------------------------------------
# Test 6: System prompt is a module-level constant and contains key instructions
# ---------------------------------------------------------------------------


def test_system_prompt_is_well_formed():
    """TEXTBOOK_FINDER_SYSTEM_PROMPT must include legal source guidance and output format."""
    assert "openstax.org" in TEXTBOOK_FINDER_SYSTEM_PROMPT
    assert "legal_source_url" in TEXTBOOK_FINDER_SYSTEM_PROMPT
    assert "source_type" in TEXTBOOK_FINDER_SYSTEM_PROMPT
    assert "piracy" in TEXTBOOK_FINDER_SYSTEM_PROMPT.lower() or "sci-hub" in TEXTBOOK_FINDER_SYSTEM_PROMPT
    assert "relevance_reason" in TEXTBOOK_FINDER_SYSTEM_PROMPT
