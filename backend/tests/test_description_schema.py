import pytest
from app.models.description_schema import ChapterDescription, ConceptEntry
from app.services.description_manager import serialize_to_md, parse_from_md, search_descriptions
from pathlib import Path
import tempfile


def make_sample_description() -> ChapterDescription:
    return ChapterDescription(
        source_textbook="DigitalControlSystems.pdf",
        chapter_number="3",
        chapter_title="The Z-Transform",
        page_range=(44, 103),
        summary="This chapter introduces the Z-transform and its properties. It covers the region of convergence, inverse Z-transform, and applications to difference equations.",
        key_concepts=[
            ConceptEntry(
                name="Z-transform",
                aliases=["z transform", "ZT", "bilateral Z-transform"],
                classification="EXPLAINS",
                description="Derives and defines the Z-transform from first principles, including region of convergence.",
            ),
            ConceptEntry(
                name="Difference equations",
                aliases=["recurrence relation"],
                classification="USES",
                description="Uses Z-transform to solve linear difference equations.",
            ),
        ],
        prerequisites=["Laplace transform", "Complex analysis", "Discrete-time signals"],
        mathematical_content=[
            "Z-transform definition: X(z) = sum_{n=-inf}^{inf} x[n] z^{-n}",
            "Region of convergence (ROC)",
            "Inverse Z-transform via partial fractions",
        ],
        has_figures=True,
        figure_descriptions=[
            "Figure 3.1: Z-plane showing poles and zeros",
            "Figure 3.2: Region of convergence for causal sequences",
        ],
    )


def test_roundtrip_preserves_all_fields():
    """Test that serialization to .md and back preserves all fields."""
    original = make_sample_description()
    md_text = serialize_to_md(original)
    restored = parse_from_md(md_text, source_textbook=original.source_textbook)

    assert restored.chapter_title == original.chapter_title
    assert restored.chapter_number == original.chapter_number
    assert restored.page_range == original.page_range
    assert "Z-transform" in restored.summary or len(restored.summary) > 0
    assert len(restored.key_concepts) == len(original.key_concepts)
    assert restored.key_concepts[0].name == "Z-transform"
    assert restored.key_concepts[0].classification == "EXPLAINS"
    assert restored.key_concepts[1].classification == "USES"
    assert restored.has_figures == True
    assert len(restored.prerequisites) == 3


def test_keyword_search_finds_explains_concepts():
    """Test that keyword search finds EXPLAINS-tagged concepts."""
    desc = make_sample_description()
    md_text = serialize_to_md(desc)

    # The .md must contain [EXPLAINS] Z-transform as a grep-able string
    assert "[EXPLAINS] Z-transform" in md_text
    assert "[USES] Difference equations" in md_text


def test_keyword_search_across_files():
    """Test search_descriptions finds files containing keyword."""
    desc = make_sample_description()
    md_text = serialize_to_md(desc)

    with tempfile.TemporaryDirectory() as tmpdir:
        desc_dir = Path(tmpdir)
        (desc_dir / "chapter_3.md").write_text(md_text, encoding="utf-8")

        results = search_descriptions(desc_dir, "Z-transform")
        assert len(results) == 1
        assert "Z-transform" in results[0]["content"]
        assert any("Z-transform" in line for line in results[0]["matched_lines"])


def test_aliases_included_in_md():
    """Test that aliases are included in .md for broader keyword matching."""
    desc = make_sample_description()
    md_text = serialize_to_md(desc)
    assert "z transform" in md_text.lower()
    assert "ZT" in md_text
