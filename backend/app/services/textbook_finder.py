"""Textbook Finder service — AI recommends relevant textbooks with legal source links."""
import json
import re
from typing import Any

from pydantic import BaseModel

from app.services.deepseek_provider import SYSTEM_PROMPT_PREFIX, DeepSeekProvider

# ---------------------------------------------------------------------------
# Piracy domain blocklist — NEVER link to these
# ---------------------------------------------------------------------------
PIRACY_DOMAINS = ["libgen", "z-lib", "sci-hub", "bookfi", "b-ok", "pdfdrive"]

# Safe fallback when a piracy URL is detected
SAFE_FALLBACK_URL = "https://openstax.org/"

# ---------------------------------------------------------------------------
# Module-level constant system prompt for DeepSeek cache hit optimisation
# ---------------------------------------------------------------------------
TEXTBOOK_FINDER_SYSTEM_PROMPT = (
    f"{SYSTEM_PROMPT_PREFIX}\n\n"
    "You are a knowledgeable academic librarian helping students find legal, openly accessible"
    " textbooks and course materials.\n\n"
    "When given a list of course material descriptions, you:\n"
    "1. Infer the subject/topic from the content.\n"
    "2. Recommend 3–5 relevant textbooks.\n"
    "3. For each textbook provide:\n"
    "   - title: full book title\n"
    "   - author: primary author(s)\n"
    "   - isbn: ISBN-13 if known, else empty string\n"
    "   - relevance_reason: one sentence explaining why this book is relevant\n"
    "   - legal_source_url: a LEGAL URL where the book can be found or purchased.\n"
    "     Prefer open sources: openstax.org, ocw.mit.edu, books.google.com.\n"
    "     Acceptable paid sources: springer.com, wiley.com, pearson.com, amazon.com.\n"
    "     NEVER use piracy sites (libgen, z-lib, sci-hub, etc.).\n"
    "   - source_type: one of 'open_access', 'publisher', 'library_catalog', 'preview'\n\n"
    "Return a JSON array (not an object) of recommendation objects, like:\n"
    '[{"title": "...", "author": "...", "isbn": "...", "relevance_reason": "...", '
    '"legal_source_url": "...", "source_type": "..."}]'
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class TextbookRecommendation(BaseModel):
    title: str
    author: str
    isbn: str
    relevance_reason: str
    legal_source_url: str
    source_type: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` fences from AI output."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _is_piracy_url(url: str) -> bool:
    """Return True if *url* contains any known piracy domain."""
    lower = url.lower()
    return any(domain in lower for domain in PIRACY_DOMAINS)


def _sanitise_recommendations(raw: list[dict[str, Any]]) -> list[TextbookRecommendation]:
    """Parse raw dicts, replace piracy URLs with the safe fallback, validate with Pydantic."""
    results: list[TextbookRecommendation] = []
    for item in raw:
        url = item.get("legal_source_url", "").strip()
        if not url or _is_piracy_url(url):
            url = SAFE_FALLBACK_URL
        results.append(
            TextbookRecommendation(
                title=item.get("title", "Unknown Title"),
                author=item.get("author", "Unknown Author"),
                isbn=item.get("isbn", ""),
                relevance_reason=item.get("relevance_reason", ""),
                legal_source_url=url,
                source_type=item.get("source_type", "publisher"),
            )
        )
    return results


# ---------------------------------------------------------------------------
# Main service function
# ---------------------------------------------------------------------------


async def find_textbooks(
    course_descriptions: list[str],
    provider: DeepSeekProvider,
) -> list[TextbookRecommendation]:
    """
    Ask DeepSeek to recommend 3–5 textbooks relevant to the given course descriptions.

    Args:
        course_descriptions: List of strings describing course material / chapter summaries.
        provider: An initialised DeepSeekProvider instance.

    Returns:
        List of TextbookRecommendation objects with validated, piracy-free URLs.
    """
    combined = "\n\n---\n\n".join(course_descriptions)

    messages = [
        {
            "role": "system",
            "content": TEXTBOOK_FINDER_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                "Based on these course materials, recommend 3–5 relevant textbooks.\n\n"
                f"{combined}"
            ),
        },
    ]

    raw_response: str = await provider.chat(
        messages=messages,
        json_mode=False,  # We ask for a JSON array; json_object mode requires an object root
    )

    cleaned = _strip_markdown_fences(raw_response)

    # DeepSeek sometimes wraps arrays in an object — unwrap if needed
    parsed = json.loads(cleaned)
    if isinstance(parsed, dict):
        # Try common wrapper keys
        for key in ("recommendations", "textbooks", "books", "results"):
            if key in parsed and isinstance(parsed[key], list):
                parsed = parsed[key]
                break
        else:
            # Fallback: grab the first list value found
            for val in parsed.values():
                if isinstance(val, list):
                    parsed = val
                    break
            else:
                parsed = []

    return _sanitise_recommendations(parsed)
