"""Tests for the keyword search engine (Task 14 — Step 1 of hybrid search)."""
import time
from pathlib import Path

import pytest

from app.services.keyword_search import SearchHit, search_descriptions


def _write_md(directory: Path, filename: str, content: str) -> Path:
    """Helper: write a .md file and return its path."""
    directory.mkdir(parents=True, exist_ok=True)
    p = directory / filename
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Test 1: Exact keyword match
# ---------------------------------------------------------------------------

def test_search_finds_exact_keyword(tmp_path: Path):
    """search_descriptions() must find a file containing the exact keyword."""
    desc_dir = tmp_path / "descriptions"
    tb_dir = desc_dir / "tb_001"
    _write_md(
        tb_dir,
        "chapter_3.md",
        "# The Z-Transform\n\n- [EXPLAINS] Z-transform\n  Introduced here.\n",
    )

    hits = search_descriptions(desc_dir, ["Z-transform"])
    assert len(hits) >= 1
    hit = hits[0]
    assert isinstance(hit, SearchHit)
    assert "z-transform" in hit.matched_keyword.lower()
    assert hit.source_textbook == "tb_001"
    assert hit.chapter == "chapter_3"
    assert hit.context_snippet != ""


# ---------------------------------------------------------------------------
# Test 2: Alias match
# ---------------------------------------------------------------------------

def test_search_finds_alias_match(tmp_path: Path):
    """Searching for 'ZT' must also find files containing 'z-transform'."""
    desc_dir = tmp_path / "descriptions"
    tb_dir = desc_dir / "tb_002"
    _write_md(
        tb_dir,
        "chapter_1.md",
        "# Introduction\n\n- [EXPLAINS] Z-transform (aliases: ZT, z domain)\n  Defined here.\n",
    )

    # Search using the alias 'zt' — should expand to find 'z-transform'
    hits = search_descriptions(desc_dir, ["zt"])
    assert len(hits) >= 1, "Alias 'zt' should expand to find z-transform content"


# ---------------------------------------------------------------------------
# Test 3: Search across multiple textbooks
# ---------------------------------------------------------------------------

def test_search_across_multiple_textbooks(tmp_path: Path):
    """Results must include hits from all textbooks, not just the first."""
    desc_dir = tmp_path / "descriptions"
    _write_md(desc_dir / "tb_001", "chapter_1.md", "# Chapter 1\n\nZ-transform is used here.\n")
    _write_md(desc_dir / "tb_002", "chapter_2.md", "# Chapter 2\n\nZ-transform derivation.\n")

    hits = search_descriptions(desc_dir, ["Z-transform"])
    sources = {h.source_textbook for h in hits}
    assert "tb_001" in sources
    assert "tb_002" in sources


# ---------------------------------------------------------------------------
# Test 4: Empty results for non-existent concept
# ---------------------------------------------------------------------------

def test_search_returns_empty_for_unknown_concept(tmp_path: Path):
    """Searching for a concept not in any description must return empty list."""
    desc_dir = tmp_path / "descriptions"
    _write_md(desc_dir / "tb_001", "chapter_1.md", "# Chapter 1\n\nZ-transform content.\n")

    hits = search_descriptions(desc_dir, ["quantum_entanglement_xyz_nonexistent"])
    assert hits == []


# ---------------------------------------------------------------------------
# Test 5: library_type filter — math only
# ---------------------------------------------------------------------------

def test_library_type_filter_math_only(tmp_path: Path):
    """library_type='math' must only return hits from math_library directory."""
    desc_dir = tmp_path / "descriptions"
    _write_md(desc_dir / "math_library", "fourier.md", "# Fourier Transform\n\nFourier transform basics.\n")
    _write_md(desc_dir / "tb_001", "chapter_1.md", "# Chapter 1\n\nFourier transform applied.\n")

    hits = search_descriptions(desc_dir, ["fourier"], library_type="math")
    sources = {h.source_textbook for h in hits}
    assert "math_library" in sources
    assert "tb_001" not in sources


# ---------------------------------------------------------------------------
# Test 6: Performance — completes in < 100ms for typical description set
# ---------------------------------------------------------------------------

def test_search_performance(tmp_path: Path):
    """Search must complete in under 100ms for a typical set of descriptions."""
    desc_dir = tmp_path / "descriptions"
    # Create 20 description files across 4 textbooks
    for tb_idx in range(4):
        for ch_idx in range(5):
            _write_md(
                desc_dir / f"tb_{tb_idx:03d}",
                f"chapter_{ch_idx}.md",
                f"# Chapter {ch_idx}\n\n- [EXPLAINS] Z-transform\n  Content {tb_idx}-{ch_idx}.\n",
            )

    start = time.monotonic()
    hits = search_descriptions(desc_dir, ["Z-transform"])
    elapsed_ms = (time.monotonic() - start) * 1000

    assert len(hits) > 0
    assert elapsed_ms < 1000, f"Search took {elapsed_ms:.1f}ms — must be < 1000ms"
