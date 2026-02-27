"""Step 1 of the hybrid search pipeline: keyword search across .md descriptions.

Pure Python text search — no AI, no cost, no embeddings.
"""
from pathlib import Path

from pydantic import BaseModel


class SearchHit(BaseModel):
    """A single keyword match in a description file."""
    file_path: str
    matched_keyword: str
    context_snippet: str   # 2-3 lines surrounding the match
    source_textbook: str   # Parent directory name (textbook ID)
    chapter: str           # Stem of the .md file (e.g. "chapter_3")
    content: str           # Full .md content (for Step 2 categorization)


# Common aliases for well-known STEM concepts.
# Searching for any alias also searches for the canonical name and vice-versa.
CONCEPT_ALIASES: dict[str, list[str]] = {
    "z-transform": ["z transform", "zt", "z-domain", "z domain"],
    "laplace transform": ["laplace", "s-domain", "s domain", "lt"],
    "fourier transform": ["fourier", "ft", "dft", "fft", "frequency domain"],
    "transfer function": ["tf", "h(s)", "h(z)", "g(s)", "g(z)"],
    "state space": ["state-space", "state space representation", "state variable"],
    "pid controller": ["pid", "proportional integral derivative"],
    "bode plot": ["bode diagram", "frequency response"],
    "nyquist": ["nyquist criterion", "nyquist plot", "nyquist stability"],
    "root locus": ["root-locus", "rl"],
}


def _expand_keywords(keywords: list[str]) -> list[str]:
    """Expand keywords with known aliases for broader search coverage."""
    expanded: set[str] = set()
    for kw in keywords:
        kw_lower = kw.lower()
        expanded.add(kw_lower)
        # Check if this keyword is a canonical name
        if kw_lower in CONCEPT_ALIASES:
            expanded.update(CONCEPT_ALIASES[kw_lower])
        # Check if this keyword is an alias
        for canonical, aliases in CONCEPT_ALIASES.items():
            if kw_lower in aliases:
                expanded.add(canonical)
                expanded.update(aliases)
    return list(expanded)


def _extract_context(content: str, keyword: str, context_lines: int = 2) -> str:
    """Return a snippet of `context_lines` lines around the first keyword match."""
    lines = content.split("\n")
    kw_lower = keyword.lower()
    for i, line in enumerate(lines):
        if kw_lower in line.lower():
            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines + 1)
            return "\n".join(lines[start:end])
    return ""


def search_descriptions(
    descriptions_dir: Path,
    keywords: list[str],
    library_type: str | None = None,
) -> list[SearchHit]:
    """Step 1: Keyword search across all .md description files.

    Args:
        descriptions_dir: Root directory containing description subdirectories.
        keywords: List of keywords to search for (expanded with aliases).
        library_type: Optional filter — 'math' for math_library only,
                      'course' for course-specific only, None for both.

    Returns:
        List of SearchHit objects, one per (file, keyword) match.
        A file matching multiple keywords produces multiple hits.
    """
    if not descriptions_dir.exists():
        return []

    expanded = _expand_keywords(keywords)
    results: list[SearchHit] = []

    for md_file in sorted(descriptions_dir.rglob("*.md")):
        # Apply library_type filter
        parent_name = md_file.parent.name
        if library_type == "math" and parent_name != "math_library":
            continue
        if library_type == "course" and parent_name == "math_library":
            continue

        content = md_file.read_text(encoding="utf-8")
        content_lower = content.lower()

        for kw in expanded:
            if kw in content_lower:
                results.append(
                    SearchHit(
                        file_path=str(md_file),
                        matched_keyword=kw,
                        context_snippet=_extract_context(content, kw),
                        source_textbook=parent_name,
                        chapter=md_file.stem,
                        content=content,
                    )
                )

    return results
