# Lazy Learn — Architectural Decisions

## Stack
- Backend: Python 3.11+, FastAPI, uvicorn, aiosqlite
- Frontend: React + TypeScript, Vite, vitest, react-katex, remark-math, rehype-katex
- Desktop: Tauri v2 (Rust shell, HTTP to FastAPI localhost:8000)
- Pixel art: CSS-only theming, Press Start 2P font, NES.css-inspired borders
- Doc parsing: PyMuPDF (PDF), python-pptx (PPTX), python-docx (DOCX)

## UI Layout
- Bookshelf: pixel art book grid (courses) → ESC or back button
- Desk: 4 columns — Input (15%) | Panel A (35%) | Panel B (35%) | Quick Ref (15%)
- Panels swap/merge, image drag-to-pin to Quick Ref as icon
- ESC always goes back one level (global keyboard listener)
- Equation hover → tooltip identification → click to explore → ESC to return
- [Generate Q&A] prominent button on left panel, context-aware

## Search Pipeline
- Step 0: AI concept extraction (deepseek-chat) — recognizes equation FORMS
- Step 1: Keyword Ctrl+F across .md descriptions — free, instant
- Step 2: AI categorizes matches as EXPLAINS or USES (deepseek-chat + JSON mode)
- Step 3: User picks subchapters (UI)
- Step 4: AI reads actual chapter content, streams explanation (deepseek-reasoner)
