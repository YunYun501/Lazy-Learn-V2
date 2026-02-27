# Lazy Learn — Learnings

## Conventions & Patterns
- DeepSeek API key: `sk-b7d20f3899e34d80bedcd47890ef4ca7`
- DeepSeek base URL: `https://api.deepseek.com`
- deepseek-chat → Steps 0/2 classification (cheap, 8K output)
- deepseek-reasoner → Step 4 explanations (64K output)
- NO embeddings, NO vector DB — AI reads .md descriptions directly
- Keyword search (Step 1) is pure Python text search — NO AI, NO cost
- Practice problems ALWAYS carry warning: "AI-generated solutions may contain errors. Verify independently."
- LaTeX: use KaTeX via react-katex. NEVER MathJax. NEVER pixelate equations.
- Font: "Press Start 2P" for UI chrome ONLY. Readable fonts for content.

## Test Data
- Textbook: `Simulation Material/Textbook/DigitalControlSystems-NeweditionI.D.LandauG.Zito.pdf`
- Lectures: `Simulation Material/University Material/[Lecture N] MECH0089*.pdf`
- Course: MECH0089 Control and Robotics


## [2026-02-27] Task 1 Spike Complete — Key Findings
- TOC extraction: Generic labels only (front-matter, fulltext, etc.) → AI fallback MANDATORY for chapter naming
- Image extraction: Figures are VECTOR GRAPHICS → use page.get_pixmap(matrix=fitz.Matrix(2,2)) NOT get_images()
- Page rendering: fitz.Matrix(2, 2) zoom → 879×1333px PNG at good quality (~92-154KB per page)
- Equations: Greek chars work (ω = \u03c9), some ASCII approximations for complex expressions
- DeepSeek classification: PASS — valid JSON in ~5.14s, EXPLAINS/USES classification works, confidence 0.9
- DeepSeek streaming: PASS — first chunk 1.63s, 94 total chunks, 5.70s total for 3-sentence response
- DeepSeek LaTeX output: Confirmed — naturally outputs \( \) and $$ delimiters, KaTeX must handle both
- Retry logic: MANDATORY — JSON mode can return empty responses
- Cache optimization: Keep system prompts constant across calls for 10x cheaper cache hits ($0.028/M vs $0.28/M)