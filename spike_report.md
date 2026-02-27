# Lazy Learn — Feasibility Spike Report
Date: 2026-02-27

## Summary
**OVERALL: GO** — All 5 critical tests passed. The hybrid search pipeline is feasible. Two critical architecture implications discovered: (1) PDF TOC has only generic labels — AI fallback is mandatory for chapter naming; (2) Figures are vector graphics — must use `page.get_pixmap()` to render pages as PNG, not `get_images()`.

---

## Test Results

### Test 1: PDF Text Extraction — PASS
- **File**: `Simulation Material/Textbook/DigitalControlSystems-NeweditionI.D.LandauG.Zito.pdf`
- **Pages**: 495 total
- **Result**: Clean, readable English text extracted. Technical content visible (control systems, identification, design).
- **Equations**: Partially readable. Greek characters work (ω = `\u03c9`). Some complex expressions rendered as ASCII approximations (e.g., `z = e^(sTs)` shown as fragmented lines). Topic keywords like "transfer function", "z-transform" are present and searchable.
- **Evidence**: `.sisyphus/evidence/task-1-pdf-text-extraction.txt`

### Test 2: TOC Extraction — PASS (with AI fallback required)
- **Result**: 12 TOC entries found, but ALL are generic labels: `front-matter`, `fulltext`, `fulltext2`, ..., `fulltext10`, `back-matter`
- **Critical Finding**: This textbook has NO named chapter bookmarks. The TOC entries only mark page boundaries, not chapter titles.
- **Implication**: AI fallback for chapter naming is **MANDATORY**. Must send first N pages to DeepSeek to identify actual chapter structure.
- **Page boundaries detected**: front-matter(p1), fulltext(p20), fulltext2(p44), fulltext3(p104), fulltext4(p187), fulltext5(p218), fulltext6(p263), fulltext7(p294), fulltext8(p331), fulltext9(p389), fulltext10(p413), back-matter(p430)
- **Evidence**: `.sisyphus/evidence/task-1-toc-extraction.txt`

### Test 3: Image Extraction — PASS (via page rendering)
- **Critical Finding**: Figures in this textbook are **VECTOR GRAPHICS** (page 45 has 263 vector drawings). `page.get_images()` returns 0 raster images on typical content pages.
- **Solution**: Use `page.get_pixmap(matrix=fitz.Matrix(2, 2))` to render full pages as PNG. This captures all vector graphics.
- **Quality**: `fitz.Matrix(2, 2)` zoom produces 879×1333px images at ~92-154KB per page — excellent quality.
- **Evidence**: `.sisyphus/evidence/task-1-images/page45_rendered.png` (vector drawing page), `.sisyphus/evidence/task-1-images/page60_rendered.png` (equation-heavy page)

### Test 4: DeepSeek API Classification — PASS
- **Model**: `deepseek-chat`
- **Latency**: 5.14 seconds
- **Result**: Valid JSON returned with correct EXPLAINS/USES classification:
  ```json
  {
    "concept": "Z-transform",
    "classification": "EXPLAINS",
    "confidence": 0.9,
    "reason": "The chapter explicitly derives the Z-transform, covers its properties..."
  }
  ```
- **Implication**: The hybrid search Step 2 (AI categorization) is fully feasible.
- **Evidence**: `.sisyphus/evidence/task-1-deepseek-classification.json`

### Test 5: DeepSeek Streaming — PASS
- **Model**: `deepseek-chat`
- **First chunk**: 1.63 seconds (well under 10s threshold)
- **Total chunks**: 94 (well over 5 threshold)
- **Total time**: 5.70 seconds for a 3-sentence explanation
- **LaTeX in stream**: Confirmed — DeepSeek naturally outputs LaTeX notation (e.g., `\( X(z) = \sum_{n=-\infty}^{\infty} x[n] z^{-n} \)`)
- **Evidence**: `.sisyphus/evidence/task-1-streaming-test.txt`

---

## Critical Architecture Implications

1. **PDF Chapter Detection**: `doc.get_toc()` gives page boundaries but NOT chapter titles. Must use AI to identify chapter names from first N pages of each section. Page boundaries from TOC are still useful for splitting text.

2. **Image/Figure Extraction**: Do NOT use `page.get_images()` for figures — they are vector graphics and won't be found. Instead, render full pages as PNG using `page.get_pixmap(matrix=fitz.Matrix(2, 2))`. Store rendered pages for display alongside text.

3. **Equation Display**: Equations in extracted text are partially readable (keywords present, some ASCII approximations). For equation-heavy content, show the rendered page image alongside the AI explanation so users can see the original typeset equations.

4. **DeepSeek Retry Logic**: JSON mode can return empty responses (known issue). Retry logic with exponential backoff is MANDATORY on all classification calls.

5. **Streaming LaTeX**: DeepSeek naturally outputs LaTeX in its responses. The frontend KaTeX renderer must handle inline `\(` and `\)` delimiters as well as `$$` block delimiters.

6. **Cache Optimization**: System prompts must be constant across calls to maximize DeepSeek cache hits (10x cheaper: $0.028/M vs $0.28/M tokens).

---

## Go/No-Go Decision

**GO** — All critical paths validated. Proceed to Wave 1 (Tasks 2-7 in parallel).

### Risks Accepted
- Equation text quality is imperfect — mitigated by showing rendered page images
- TOC requires AI fallback — adds latency to initial import but is feasible
- DeepSeek JSON mode can return empty — mitigated by mandatory retry logic
