"""
MinerU Spike — Page-Range Extraction + Content Type Vocabulary

This spike validates MinerU's do_parse() behavior for selective extraction:
1. Page-range params (start_page_id, end_page_id) correctly limit extraction
2. Content type vocabulary is catalogued for schema design
3. Multiple sequential calls don't cause temp directory conflicts

FINDINGS:
- Page range params WORK. Output page_idx is REBASED to 0 (not original page numbers).
- Content types: text, equation, image, table, discarded
- Multiple calls safe (unique temp dirs per call)
- Model init adds ~22s per call. Batch chapters for efficiency.
"""

import json
import tempfile
import shutil
from pathlib import Path

import pytest

# Skip all tests if MinerU is not available
try:
    from mineru.cli.common import do_parse
    MINERU_AVAILABLE = True
except ImportError:
    MINERU_AVAILABLE = False

# Find test PDF
TEST_PDF = Path(__file__).parent.parent / "data" / "textbooks" / "da616ad6-23a8-4ed4-9e9c-8a7a5ef87e10" / "original.pdf"
HAS_TEST_PDF = TEST_PDF.exists()

SPIKE_RESULTS_PATH = Path(__file__).parent / "fixtures" / "spike_results.json"

skip_if_no_mineru = pytest.mark.skipif(
    not MINERU_AVAILABLE, reason="MinerU not installed"
)
skip_if_no_pdf = pytest.mark.skipif(
    not HAS_TEST_PDF, reason="Test PDF not available"
)


def _run_mineru(pdf_bytes: bytes, start_page: int, end_page: int, output_dir: str) -> list[dict]:
    """Helper: run MinerU do_parse and return content list entries."""
    do_parse(
        output_dir=output_dir,
        pdf_file_names=["document"],
        pdf_bytes_list=[pdf_bytes],
        p_lang_list=["en"],
        backend="pipeline",
        parse_method="auto",
        formula_enable=True,
        table_enable=True,
        f_dump_md=True,
        f_dump_content_list=True,
        f_dump_middle_json=False,
        f_dump_model_output=False,
        f_dump_orig_pdf=False,
        f_draw_layout_bbox=False,
        f_draw_span_bbox=False,
        start_page_id=start_page,
        end_page_id=end_page,
    )
    content_path = Path(output_dir) / "document" / "auto" / "document_content_list.json"
    assert content_path.exists(), f"MinerU content list not found at {content_path}"
    return json.loads(content_path.read_text(encoding="utf-8"))


@skip_if_no_mineru
@skip_if_no_pdf
def test_page_range_extraction():
    """Verify start_page_id/end_page_id correctly limit extraction range.

    FINDING: Page range params WORK. Output page_idx is REBASED to 0.
    When extracting pages 22-35 (14 pages), output page_idx ranges from 0 to 13.
    Caller must add start_page_id offset to recover original page numbers.
    """
    pdf_bytes = TEST_PDF.read_bytes()
    temp_dir = tempfile.mkdtemp()
    try:
        start, end = 22, 35  # Introduction chapter (pages 23-35, 0-indexed: 22-35)
        entries = _run_mineru(pdf_bytes, start, end, temp_dir)

        assert len(entries) > 0, "Expected content entries from extraction"

        # Collect page indices
        page_indices = {e.get("page_idx") for e in entries if e.get("page_idx") is not None}
        assert len(page_indices) > 0, "Expected page indices in output"

        # Page indices should be rebased to 0 (relative to extracted range)
        expected_pages = end - start + 1  # inclusive range: 14 pages = indices 0-13
        max_idx = max(page_indices)
        assert max_idx < expected_pages, (
            f"Output page_idx max ({max_idx}) should be < {expected_pages} "
            f"(rebased to 0 for {expected_pages}-page extraction)"
        )
        assert min(page_indices) == 0, "First page_idx should be 0 (rebased)"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@skip_if_no_mineru
@skip_if_no_pdf
def test_content_type_vocabulary():
    """Catalog all content type values from MinerU output.

    FINDING: Types found: text, equation, image, table, discarded
    - text: paragraphs with text_level, bbox, page_idx
    - equation: LaTeX text + rendered image (img_path, text_format='latex')
    - image: figures with img_path, image_caption, image_footnote
    - table: tabular content
    - discarded: headers/footers to skip
    """
    pdf_bytes = TEST_PDF.read_bytes()
    temp_dir = tempfile.mkdtemp()
    try:
        # Extract pages 22-35 (Introduction) — known to have text + equations + images
        entries = _run_mineru(pdf_bytes, 22, 35, temp_dir)

        types_seen = {e.get("type") for e in entries}
        # At minimum we expect text and discarded
        assert "text" in types_seen, "Expected 'text' type in content"
        assert len(types_seen) >= 2, f"Expected at least 2 distinct types, got: {types_seen}"

        # Verify entry structure per type
        for entry in entries:
            assert "type" in entry, "Every entry must have a 'type' field"
            assert "page_idx" in entry, "Every entry must have a 'page_idx' field"
            if entry["type"] == "equation":
                assert "text" in entry, "Equations should have LaTeX text"
            if entry["type"] == "image":
                assert "img_path" in entry, "Images should have img_path"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@skip_if_no_mineru
@skip_if_no_pdf
def test_multiple_sequential_calls():
    """Verify multiple MinerU calls don't conflict (temp dir isolation).

    FINDING: No conflicts. Each call uses unique temp dir via tempfile.mkdtemp().
    Sequential calls with different page ranges all produce valid output.
    """
    pdf_bytes = TEST_PDF.read_bytes()
    results = []

    # Three calls with different page ranges
    ranges = [(22, 30), (99, 105), (199, 203)]
    for start, end in ranges:
        temp_dir = tempfile.mkdtemp()
        try:
            entries = _run_mineru(pdf_bytes, start, end, temp_dir)
            results.append(len(entries))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    # All 3 calls should have produced output
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    for i, count in enumerate(results):
        assert count > 0, f"Call {i+1} (pages {ranges[i]}) produced 0 entries"


@pytest.fixture(autouse=True)
def _spike_results_exist():
    """Verify spike_results.json exists (created by orchestrator, not tests)."""
    yield
    # Post-test check: spike_results.json should exist
    assert SPIKE_RESULTS_PATH.exists(), (
        f"spike_results.json not found at {SPIKE_RESULTS_PATH}. "
        "This file documents MinerU content types and should be created during the spike."
    )
