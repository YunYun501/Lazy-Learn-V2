# Lazy Learn — AI-Powered STEM Study Assistant

## TL;DR

> **Quick Summary**: Build a locally-run desktop study assistant that uses DeepSeek AI to cross-reference STEM textbooks. Students import textbook PDFs → app breaks them into chapters with AI-generated descriptions → hybrid search (concept extraction + keyword + AI categorization) finds relevant sections → AI generates combined explanations with LaTeX equations and practice problems. Pixel art bookshelf/desk UI with high-fidelity equation rendering.
> 
> **Deliverables**:
> - Python (FastAPI) backend with document processing pipeline + DeepSeek AI integration
> - React + TypeScript frontend with pixel art theme + KaTeX equation rendering
> - Tauri desktop shell wrapping both
> - 5 feature modules: LMS Downloader, Material Organizer, Textbook Finder, Cross-Referencer (core), Pixel Art UI
> 
> **Estimated Effort**: XL
> **Parallel Execution**: YES — 6 waves
> **Critical Path**: Validation Spike → Doc Processing → Description Generation → Search Pipeline → AI Explanation Engine → UI Integration

---

## Context

### Original Request
Build "Lazy Learn" — an AI study assistant for STEM students that can download course materials, organize them, find relevant textbooks, and most importantly, cross-reference content across multiple textbooks to generate explanations and practice problems. The UI should be pixel art styled. Uses DeepSeek API primarily, with optional OpenAI GPT-4o for vision tasks.

### Interview Summary
**Key Discussions**:
- **Architecture**: Python (FastAPI) + React/TypeScript + Tauri confirmed after exploring alternatives
- **No embeddings/vector DB**: User explicitly rejected RAG approach. AI reads .md descriptions directly, keyword search filters first
- **Hybrid search flow**: Step 0 (AI concept extraction) → Step 1 (keyword Ctrl+F) → Step 2 (AI categorize EXPLAINS/USES) → Step 3 (user picks) → Step 4 (AI deep explanation)
- **Equation intelligence**: AI must recognize equation FORMS not just literal text. Y(z) = az/(z-b) is a Z-transform regardless of a,b values
- **Two libraries**: Math Library (always available) + Course-Specific Library (~5 textbooks per course)
- **UI layout**: Bookshelf (courses) → Desk (open book) → Left panel (chat) + Right panel (AI book answer)
- **Graphs/Images**: STEM textbooks have critical figures. Must extract and display images from PDFs
- **LaTeX is critical**: All equations must render with KaTeX, not pixelated. AI outputs Markdown+LaTeX
- **DeepSeek models**: deepseek-chat for classification (8K output, cheap), deepseek-reasoner for explanations (64K output)
- **Practice problems**: AI generates questions + worked solutions with "verify solutions" warning (39.8% math error rate)
- **MVP priority**: Module #4 (cross-referencer) first, with minimal Module #2 (doc processing) as prerequisite
- **TDD**: pytest (backend) + vitest (frontend) from the start
- **Personal tool first**: Expandable to other users later
- **Streaming**: Must stream AI explanations (30-90 sec latency otherwise)
- **OpenAI optional**: For vision tasks (scanned PDFs, graph analysis). User provides own GPT subscription

### Research Findings
- **DeepSeek API**: 128K context, OpenAI-compatible endpoints, no hard rate limits (dynamic throttling), cache hits 10x cheaper
- **Document Parsing**: PyMuPDF (fast, layout-aware, image extraction), python-pptx (slide structure), python-docx
- **Pixel Art**: NES.css, 8bitcn/ui for CSS theming. "Press Start 2P" font. Modern pixel art style (Celeste/Stardew Valley)
- **Tauri+FastAPI**: Sidecar pattern, HTTP communication, ~55MB installer, 2-5 sec Python startup
- **Textbook TOC**: PyMuPDF `get_toc()` for bookmarks, AI fallback for PDFs without bookmarks
- **Browser automation**: Playwright from Python backend, Moodle-DL (400+ stars) as reference
- **Textbook sources**: OpenStax (free), Google Books API (metadata), Open Library API

### Metis Review
**Identified Gaps** (addressed):
- Equation extraction feasibility unknown → Added validation spike as Task #1
- Math Library undefined → Deferred to post-MVP, user builds library over time
- DeepSeek model selection per step → deepseek-chat for Steps 0/2, deepseek-reasoner for Step 4
- Math error rate 39.8% → Mandatory "verify solutions" disclaimer on all generated problems
- Chapter boundary detection → PyMuPDF TOC extraction + AI fallback for bookmarkless PDFs
- App state persistence → SQLite for metadata, filesystem for descriptions and extracted content
- No offline story → Keyword search works offline; AI features require internet. Stated explicitly.
- JSON mode empty responses → Retry logic with exponential backoff on all API calls

---

## Work Objectives

### Core Objective
Build a locally-run STEM study assistant that intelligently cross-references textbook content using a hybrid search pipeline (concept extraction → keyword search → AI categorization → AI explanation), with a pixel art bookshelf/desk UI and high-fidelity LaTeX equation rendering.

### Concrete Deliverables
- `backend/` — Python FastAPI server with document processing + AI orchestration
- `frontend/` — React + TypeScript app with pixel art theme + KaTeX
- `src-tauri/` — Tauri desktop shell configuration
- `descriptions/` — Generated .md descriptions for all processed documents
- `.sisyphus/evidence/` — QA evidence screenshots and test outputs

### Definition of Done
- [ ] `pytest` passes all backend tests
- [ ] `vitest` passes all frontend tests
- [ ] User can import a PDF textbook and get auto-generated chapter descriptions
- [ ] User can type a query → see categorized results (EXPLAINS/USES) → select → get AI explanation with LaTeX
- [ ] AI generates practice problems with solutions + "verify" warning
- [ ] Pixel art bookshelf → desk → chat+book UI is functional
- [ ] Images/graphs from textbooks are extracted and viewable
- [ ] Existing Simulation Material/ works end-to-end as test data

### Must Have
- Hybrid search pipeline (concept extraction → keyword → AI categorization → AI explanation)
- EXPLAINS vs USES distinction in all descriptions and search results
- KaTeX rendering for all equations (never pixelated equations)
- Image extraction from PDFs (graphs, figures, diagrams)
- Streaming AI responses for explanations
- Conversational follow-ups ("give me more examples", "explain differently")
- Practice question + solution generation
- "Verify solutions independently" warning on all generated problems
- Retry logic with exponential backoff on all DeepSeek API calls
- Pixel art UI chrome with high-fidelity content rendering
- DeepSeek API key configuration (provided key as default)
- Optional OpenAI API key configuration for vision tasks

### Must NOT Have (Guardrails)
- NO embeddings, vector databases, or ChromaDB — user explicitly rejected this
- NO pixelated equations — all math must render with KaTeX
- NO direct textbook downloads — app recommends, user downloads themselves
- NO credential storage — LMS login is via embedded browser, app never stores passwords
- NO cloud deployment — locally run desktop app only
- NO mobile app
- NO real-time collaboration or multi-user features
- NO over-abstraction — keep code direct and readable
- NO AI-generated content presented without source attribution
- NO practice solutions presented as verified — always carry warning disclaimer

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: NO (greenfield project)
- **Automated tests**: TDD from the start
- **Backend framework**: pytest + pytest-asyncio (FastAPI async tests)
- **Frontend framework**: vitest + React Testing Library
- **If TDD**: Each task follows RED (failing test) → GREEN (minimal impl) → REFACTOR

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Frontend/UI**: Use Playwright (playwright skill) — Navigate, interact, assert DOM, screenshot
- **API/Backend**: Use Bash (curl/httpie) — Send requests, assert status + response fields
- **Document Processing**: Use Bash (python scripts) — Import test PDFs, verify output files exist and contain expected content
- **AI Integration**: Use Bash (python scripts) — Send test prompts, verify response structure and content

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 0 (Validation — MUST PASS before anything else):
└── Task 1: Feasibility validation spike [deep]

Wave 1 (Foundation — after spike passes, MAX PARALLEL):
├── Task 2: Python backend scaffolding + FastAPI + pytest [quick]
├── Task 3: React frontend scaffolding + Vite + vitest + KaTeX [quick]
├── Task 4: Tauri shell scaffolding (wraps frontend + spawns backend) [quick]
├── Task 5: DeepSeek AI provider abstraction layer [quick]
├── Task 6: Description schema definition (.md format spec) [quick]
└── Task 7: SQLite metadata store + filesystem layout [quick]

Wave 2 (Core Pipeline — after Wave 1, MAX PARALLEL):
├── Task 8: PDF parser — text + image + TOC extraction (depends: 2, 7) [deep]
├── Task 9: PPT/DOCX parser — slide/paragraph extraction (depends: 2, 7) [unspecified-high]
├── Task 10: AI description generator — chapter/subchapter .md files (depends: 5, 6, 8) [deep]
├── Task 11: Pixel art design system — theme tokens, fonts, base components (depends: 3) [visual-engineering]
└── Task 12: OpenAI vision provider (optional) — behind same abstraction (depends: 5) [quick]

Wave 3 (Search + UI — after Wave 2, MAX PARALLEL):
├── Task 13: Step 0 — AI concept/equation extractor (depends: 5) [deep]
├── Task 14: Step 1 — Keyword search engine across descriptions (depends: 6, 10) [unspecified-high]
├── Task 15: Step 2 — AI categorization EXPLAINS/USES (depends: 5, 14) [deep]
├── Task 16: Bookshelf view — course grid + book selection (depends: 11) [visual-engineering]
├── Task 17: Desk view — left chat panel + right book panel (depends: 11) [visual-engineering]
└── Task 18: KaTeX + Markdown content renderer with image support (depends: 3) [unspecified-high]

Wave 4 (Explanation Engine + UI Integration — after Wave 3):
├── Task 19: Step 4 — AI explanation generator with streaming (depends: 5, 15) [deep]
├── Task 20: Practice question + solution generator with warning (depends: 19) [deep]
├── Task 21: Conversational follow-up handler (depends: 19) [unspecified-high]
├── Task 22: Search results UI — categorized list with EXPLAINS/USES badges (depends: 15, 17) [visual-engineering]
├── Task 23: Explanation view — streaming book panel with LaTeX + images (depends: 18, 19) [visual-engineering]
└── Task 24: Raw textbook viewer — PDF page display with images (depends: 8, 17) [visual-engineering]

Wave 5 (Post-MVP Modules — after Wave 4):
├── Task 25: Material Organizer — auto-categorize files into folders (depends: 8, 9, 10) [unspecified-high]
├── Task 26: Textbook Finder — AI recommends textbooks + links (depends: 5, 10) [unspecified-high]
├── Task 27: LMS Downloader — Playwright embedded browser for Moodle (depends: 2, 4) [deep]
├── Task 28: Loading/splash screen — pixel art startup animation (depends: 11) [visual-engineering]
└── Task 29: Settings panel — API keys, download folder, course management (depends: 11, 17) [visual-engineering]

Wave FINAL (After ALL tasks — independent review, 4 parallel):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA — full flow with simulation materials (unspecified-high)
└── Task F4: Scope fidelity check (deep)

Critical Path: T1 → T2 → T8 → T10 → T14 → T15 → T19 → T23 → F1-F4
Parallel Speedup: ~65% faster than sequential
Max Concurrent: 6 (Waves 1 & 2)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | ALL | 0 |
| 2 | 1 | 8, 9, 27 | 1 |
| 3 | 1 | 11, 18 | 1 |
| 4 | 1 | 27 | 1 |
| 5 | 1 | 10, 12, 13, 15, 19, 26 | 1 |
| 6 | 1 | 10, 14 | 1 |
| 7 | 1 | 8, 9 | 1 |
| 8 | 2, 7 | 10, 24, 25 | 2 |
| 9 | 2, 7 | 25 | 2 |
| 10 | 5, 6, 8 | 14, 25, 26 | 2 |
| 11 | 3 | 16, 17, 22, 23, 24, 28, 29 | 2 |
| 12 | 5 | — | 2 |
| 13 | 5 | — | 3 |
| 14 | 6, 10 | 15, 22 | 3 |
| 15 | 5, 14 | 19, 22 | 3 |
| 16 | 11 | — | 3 |
| 17 | 11 | 22, 23, 24, 29 | 3 |
| 18 | 3 | 23 | 3 |
| 19 | 5, 15 | 20, 21, 23 | 4 |
| 20 | 19 | — | 4 |
| 21 | 19 | — | 4 |
| 22 | 15, 17 | — | 4 |
| 23 | 18, 19 | — | 4 |
| 24 | 8, 17 | — | 4 |
| 25 | 8, 9, 10 | — | 5 |
| 26 | 5, 10 | — | 5 |
| 27 | 2, 4 | — | 5 |
| 28 | 11 | — | 5 |
| 29 | 11, 17 | — | 5 |

### Agent Dispatch Summary

- **Wave 0**: 1 — T1 → `deep`
- **Wave 1**: 6 — T2-T4 → `quick`, T5 → `quick`, T6 → `quick`, T7 → `quick`
- **Wave 2**: 5 — T8 → `deep`, T9 → `unspecified-high`, T10 → `deep`, T11 → `visual-engineering`, T12 → `quick`
- **Wave 3**: 6 — T13 → `deep`, T14 → `unspecified-high`, T15 → `deep`, T16 → `visual-engineering`, T17 → `visual-engineering`, T18 → `unspecified-high`
- **Wave 4**: 6 — T19 → `deep`, T20 → `deep`, T21 → `unspecified-high`, T22 → `visual-engineering`, T23 → `visual-engineering`, T24 → `visual-engineering`
- **Wave 5**: 5 — T25 → `unspecified-high`, T26 → `unspecified-high`, T27 → `deep`, T28 → `visual-engineering`, T29 → `visual-engineering`
- **FINAL**: 4 — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.


- [x] 1. Feasibility Validation Spike — PDF Extraction + DeepSeek API

  **What to do**:
  - Test PyMuPDF text extraction on the existing `Simulation Material/Textbook/DigitalControlSystems-NeweditionI.D.LandauG.Zito.pdf`
  - Extract text from pages 1-20. Inspect: Are equations readable or garbled Unicode?
  - Extract TOC using `doc.get_toc()`. Count entries. Print first 20.
  - Extract images from 3-5 pages. Verify images are saved as PNG/JPG and contain graphs/figures.
  - Test DeepSeek API: Send a sample chapter text + ask it to generate an EXPLAINS/USES classification as JSON. Verify response structure.
  - Test DeepSeek API: Send a math question + ask it to identify the underlying equation/axiom. Verify concept extraction works.
  - Test DeepSeek streaming: Verify `stream=True` returns chunks progressively.
  - Test retry logic: Verify exponential backoff works when API returns empty or errors.
  - Measure: Token count for a typical chapter (~5 pages of text). Estimate how many descriptions fit in 128K.
  - If equations are garbled: Document this as a known limitation. Equations will be described in plain text in descriptions. Original PDF images serve as visual reference.
  - Write a `spike_report.md` summarizing all findings with pass/fail for each test.

  **Must NOT do**:
  - Do not build any production code — this is purely investigative
  - Do not install unnecessary dependencies — only what's needed for the spike
  - Do not attempt to fix PyMuPDF equation extraction if it fails — document and move on

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Investigative work requiring multiple experiments, measurement, and judgment calls
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: Not needed — no browser work in this spike

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 0 (solo — gate for everything)
  - **Blocks**: ALL tasks (Tasks 2-29, F1-F4)
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `Simulation Material/Textbook/DigitalControlSystems-NeweditionI.D.LandauG.Zito.pdf` — The actual textbook PDF to test against
  - `Simulation Material/University Material/[Lecture 1] MECH0089*.pdf` — Lecture slides to test slide-format PDF extraction

  **External References**:
  - PyMuPDF docs: `https://pymupdf.readthedocs.io/en/latest/` — `page.get_text()`, `doc.get_toc()`, `page.get_images()`
  - DeepSeek API: `https://api-docs.deepseek.com/` — Chat completions endpoint, streaming, JSON mode
  - DeepSeek pricing: Cache hit $0.028/M vs miss $0.28/M tokens — test prompt structure for cache efficiency

  **WHY Each Reference Matters**:
  - The textbook PDF is the real-world test data. If extraction fails here, the entire approach needs revision.
  - DeepSeek API behavior under real prompts determines whether the hybrid search pipeline is feasible.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: PDF text extraction produces readable output
    Tool: Bash (python script)
    Preconditions: PyMuPDF installed, textbook PDF exists at Simulation Material/Textbook/
    Steps:
      1. Run: python -c "import fitz; doc=fitz.open('Simulation Material/Textbook/DigitalControlSystems-NeweditionI.D.LandauG.Zito.pdf'); print(doc[5].get_text())"
      2. Inspect output for readable English text (not garbled Unicode)
      3. Check if mathematical content is present (even if imperfect)
    Expected Result: At least 80% of text content is readable English. Math may be imperfect but topic keywords (like 'transfer function', 'z-transform') are present.
    Failure Indicators: Output is mostly Unicode symbols, completely empty, or raises exception
    Evidence: .sisyphus/evidence/task-1-pdf-text-extraction.txt

  Scenario: TOC extraction finds chapter structure
    Tool: Bash (python script)
    Preconditions: Same as above
    Steps:
      1. Run: python -c "import fitz; doc=fitz.open('Simulation Material/Textbook/DigitalControlSystems-NeweditionI.D.LandauG.Zito.pdf'); toc=doc.get_toc(); print(f'{len(toc)} entries'); [print(e) for e in toc[:20]]"
      2. Check output contains hierarchical entries with page numbers
    Expected Result: At least 5 TOC entries with [level, title, page_number] format
    Failure Indicators: Empty list (no bookmarks) — triggers AI-based TOC fallback requirement
    Evidence: .sisyphus/evidence/task-1-toc-extraction.txt

  Scenario: Image extraction saves viewable files
    Tool: Bash (python script)
    Preconditions: Same as above
    Steps:
      1. Run script that extracts images from pages 10-15 using fitz page.get_images() + doc.extract_image()
      2. Save images to .sisyphus/evidence/task-1-images/
      3. Verify at least 1 image file exists and is > 1KB
    Expected Result: 1+ PNG/JPG images extracted, each > 1KB, visually containing graphs or figures
    Failure Indicators: No images found, or all images are tiny icons/bullets
    Evidence: .sisyphus/evidence/task-1-images/

  Scenario: DeepSeek API responds with valid classification
    Tool: Bash (python script with requests)
    Preconditions: DeepSeek API key available
    Steps:
      1. Send POST to https://api.deepseek.com/chat/completions with model=deepseek-chat
      2. System prompt: 'Classify whether this chapter EXPLAINS or USES the following concept. Return JSON: {"concept": "...", "classification": "EXPLAINS|USES", "confidence": 0.0-1.0, "reason": "..."}'
      3. User message: sample chapter description + 'Concept: Z-transform'
      4. Parse JSON response
    Expected Result: Valid JSON with classification field containing either 'EXPLAINS' or 'USES'
    Failure Indicators: Non-JSON response, empty content, API error, timeout > 60s
    Evidence: .sisyphus/evidence/task-1-deepseek-classification.json

  Scenario: DeepSeek streaming works progressively
    Tool: Bash (python script)
    Preconditions: Same as above
    Steps:
      1. Send streaming request (stream=true) to DeepSeek
      2. Collect chunks with timestamps
      3. Verify first chunk arrives within 10 seconds
      4. Verify total chunks > 5 (not a single blob)
    Expected Result: Progressive chunk delivery, first chunk < 10s
    Failure Indicators: All content arrives in single chunk, or first chunk > 30s
    Evidence: .sisyphus/evidence/task-1-streaming-test.txt
  ```

  **Evidence to Capture:**
  - [ ] spike_report.md with pass/fail for each test
  - [ ] Extracted text sample, TOC listing, image files, API response JSON, streaming timestamps

  **Commit**: YES
  - Message: `spike(core): validate PDF extraction and DeepSeek API feasibility`
  - Files: `spike_report.md`, test scripts
  - Pre-commit: N/A (spike only)

---

- [x] 2. Python Backend Scaffolding — FastAPI + pytest + Project Structure

  **What to do**:
  - Create `backend/` directory with Python project structure:
    - `backend/pyproject.toml` — Dependencies: fastapi, uvicorn, pymupdf, python-pptx, python-docx, httpx (for DeepSeek), pydantic
    - `backend/app/main.py` — FastAPI app with CORS middleware (for React frontend on different port)
    - `backend/app/routers/` — Empty router directory with `__init__.py`
    - `backend/app/services/` — Empty services directory with `__init__.py`
    - `backend/app/models/` — Pydantic models directory with `__init__.py`
    - `backend/app/core/config.py` — Settings via pydantic-settings: DEEPSEEK_API_KEY, OPENAI_API_KEY (optional), DATA_DIR, DESCRIPTIONS_DIR
    - `backend/tests/` — pytest directory with `conftest.py` (FastAPI test client fixture)
  - TDD: Write a test that verifies GET `/health` returns `{"status": "ok"}`
  - Implement the health endpoint to make test pass
  - Verify `pytest` runs and passes

  **Must NOT do**:
  - Do not implement any business logic — just scaffolding
  - Do not hardcode API keys — use environment variables / config

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Standard scaffolding with well-known patterns
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 3, 4, 5, 6, 7)
  - **Blocks**: Tasks 8, 9, 27
  - **Blocked By**: Task 1

  **References**:

  **External References**:
  - FastAPI docs: `https://fastapi.tiangolo.com/` — App setup, CORS middleware, testing
  - pytest-asyncio: `https://pytest-asyncio.readthedocs.io/` — Async test fixtures for FastAPI
  - pydantic-settings: `https://docs.pydantic.dev/latest/concepts/pydantic_settings/` — Environment-based config

  **WHY Each Reference Matters**:
  - FastAPI CORS is critical — frontend runs on different port (Vite dev server :5173 vs FastAPI :8000)
  - pydantic-settings pattern ensures API keys are never hardcoded

  **Acceptance Criteria**:
  - [ ] Test file: `backend/tests/test_health.py`
  - [ ] `cd backend && pytest` → PASS (1 test, 0 failures)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: FastAPI server starts and health endpoint works
    Tool: Bash (curl)
    Preconditions: backend virtualenv created, dependencies installed
    Steps:
      1. Start server: cd backend && uvicorn app.main:app --port 8000 &
      2. Wait 3 seconds
      3. Run: curl -s http://localhost:8000/health
      4. Kill server
    Expected Result: JSON response `{"status": "ok"}` with HTTP 200
    Failure Indicators: Connection refused, non-200 status, missing JSON
    Evidence: .sisyphus/evidence/task-2-health-endpoint.txt
  ```

  **Commit**: YES (groups with T3-T7)
  - Message: `feat(scaffold): python backend — FastAPI + pytest + project structure`
  - Files: `backend/**`
  - Pre-commit: `cd backend && pytest`

---

- [x] 3. React Frontend Scaffolding — Vite + TypeScript + vitest + KaTeX

  **What to do**:
  - Create `frontend/` with Vite + React + TypeScript:
    - `npx create-vite frontend --template react-ts`
    - Install: `react-katex`, `katex`, `react-markdown`, `remark-math`, `rehype-katex`
    - Install dev: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`
    - Configure `vitest.config.ts` with jsdom environment
  - Create `frontend/src/App.tsx` — minimal shell that renders "Lazy Learn" title
  - Create `frontend/src/components/` directory
  - Create `frontend/src/api/` directory — for backend API client
  - TDD: Write test that verifies App component renders "Lazy Learn"
  - TDD: Write test that verifies KaTeX renders a LaTeX equation `$E = mc^2$` without error
  - Implement to make tests pass

  **Must NOT do**:
  - Do not add pixel art styling yet — that's Task 11
  - Do not build any pages — just the shell + KaTeX proof

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Standard React scaffolding
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 4, 5, 6, 7)
  - **Blocks**: Tasks 11, 18
  - **Blocked By**: Task 1

  **References**:

  **External References**:
  - Vite: `https://vitejs.dev/guide/` — Project creation
  - react-katex: `https://www.npmjs.com/package/react-katex` — KaTeX React wrapper
  - remark-math + rehype-katex: For rendering LaTeX inside Markdown content

  **Acceptance Criteria**:
  - [ ] Test files in `frontend/src/__tests__/`
  - [ ] `cd frontend && npx vitest run` → PASS (2 tests, 0 failures)
  - [ ] KaTeX CSS imported, equation renders without console errors

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Vite dev server starts and renders app
    Tool: Bash
    Preconditions: frontend dependencies installed
    Steps:
      1. cd frontend && npm run dev &
      2. Wait 5 seconds
      3. curl -s http://localhost:5173 | grep -c 'Lazy Learn'
      4. Kill server
    Expected Result: HTML contains 'Lazy Learn' text
    Failure Indicators: Connection refused, empty page, missing text
    Evidence: .sisyphus/evidence/task-3-frontend-renders.txt
  ```

  **Commit**: YES (groups with T2, T4-T7)
  - Message: `feat(scaffold): react frontend — Vite + TypeScript + KaTeX + vitest`
  - Files: `frontend/**`
  - Pre-commit: `cd frontend && npx vitest run`

---

- [x] 4. Tauri Desktop Shell — Wraps Frontend + Spawns Python Backend

  **What to do**:
  - Initialize Tauri in the project root: `npm create tauri-app` or manual setup
  - Configure `src-tauri/tauri.conf.json`:
    - Window title: "Lazy Learn"
    - Dev URL: `http://localhost:5173` (Vite dev server)
    - Build: point to `frontend/dist`
    - Window size: 1280x800 default, resizable
  - Configure sidecar or shell command to spawn Python backend on app startup:
    - On dev: `cd backend && uvicorn app.main:app --port 8000`
    - On prod: bundled Python executable via PyInstaller (deferred to Task 28)
  - Add Tauri allowlist for HTTP to localhost:8000 (backend communication)
  - TDD: Verify `cargo build` succeeds for the Tauri shell
  - Create a basic `src-tauri/src/main.rs` that spawns the Python process and manages its lifecycle (start on launch, kill on close)

  **Must NOT do**:
  - Do not implement PyInstaller bundling — that's post-MVP
  - Do not add Tauri IPC commands — all communication goes through HTTP to FastAPI

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Tauri setup is documented and straightforward
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 5, 6, 7)
  - **Blocks**: Task 27
  - **Blocked By**: Task 1

  **References**:

  **External References**:
  - Tauri v2 guides: `https://v2.tauri.app/start/` — Setup and configuration
  - Tauri + FastAPI template: `fudanglp/tauri-fastapi-full-stack-template` on GitHub — sidecar pattern reference
  - Tauri shell plugin: For spawning Python process as a sidecar

  **Acceptance Criteria**:
  - [ ] `cd src-tauri && cargo build` → succeeds
  - [ ] `cargo tauri dev` opens a window showing the React frontend

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Tauri builds without errors
    Tool: Bash
    Preconditions: Rust toolchain installed, Tauri CLI installed
    Steps:
      1. Run: cd src-tauri && cargo check
      2. Verify exit code 0
    Expected Result: No compilation errors
    Failure Indicators: Cargo errors about missing crates or compilation failures
    Evidence: .sisyphus/evidence/task-4-tauri-build.txt
  ```

  **Commit**: YES (groups with T2, T3, T5-T7)
  - Message: `feat(scaffold): tauri desktop shell with python sidecar`
  - Files: `src-tauri/**`
  - Pre-commit: `cd src-tauri && cargo check`

---

- [x] 5. DeepSeek AI Provider Abstraction Layer

  **What to do**:
  - Create `backend/app/services/ai_provider.py` — Abstract base class for AI providers:
    - `async def chat(messages, model, stream, json_mode) -> str | AsyncGenerator`
    - `async def extract_concepts(user_query: str) -> list[str]` — Step 0
    - `async def classify_matches(descriptions: list[dict], concept: str) -> list[ClassifiedMatch]` — Step 2
    - `async def generate_explanation(content_chunks: list[str], query: str, stream: bool) -> str | AsyncGenerator` — Step 4
    - `async def generate_practice_problems(content: str, topic: str, count: int) -> PracticeProblems` — Practice Q&A
  - Create `backend/app/services/deepseek_provider.py` — DeepSeek implementation:
    - Uses httpx async client to call `https://api.deepseek.com/chat/completions`
    - Model selection: `deepseek-chat` for Steps 0/2 (classification, cheap), `deepseek-reasoner` for Step 4 (explanation, 64K output)
    - Implements streaming via SSE parsing for Step 4
    - JSON mode for classification responses with retry on empty content
    - Exponential backoff retry logic (3 retries, 2/4/8 sec delays) for all calls
    - System prompt structuring for cache hit optimization (constant preamble + variable query)
    - Timeout handling: 60s for classification, 120s for explanations
  - Create Pydantic models:
    - `ClassifiedMatch(source, chapter, subchapter, classification: EXPLAINS|USES, confidence, reason)`
    - `PracticeProblems(problems: list[Problem])` where Problem has `question, solution, warning_disclaimer`
    - `ConceptExtraction(concepts: list[str], equations: list[str])`
  - All practice problem responses MUST include the `warning_disclaimer` field: "AI-generated solutions may contain errors. Verify independently."
  - TDD: Test concept extraction with mocked API response
  - TDD: Test classification with mocked API response
  - TDD: Test retry logic triggers on empty response
  - TDD: Test that practice problems always contain warning disclaimer

  **Must NOT do**:
  - Do not implement OpenAI provider here — that's Task 12
  - Do not hardcode API key — read from config (Task 2)
  - Do not use any embedding or vector DB APIs

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: API client with well-defined patterns, mostly httpx + Pydantic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4, 6, 7)
  - **Blocks**: Tasks 10, 12, 13, 15, 19, 26
  - **Blocked By**: Task 1

  **References**:

  **External References**:
  - DeepSeek API docs: `https://api-docs.deepseek.com/` — Chat completions, streaming, JSON mode
  - DeepSeek pricing: Cache hit $0.028/M, miss $0.28/M — structure system prompts for cache efficiency
  - httpx async streaming: `https://www.python-httpx.org/async/#streaming-responses` — SSE streaming pattern

  **WHY Each Reference Matters**:
  - DeepSeek API is OpenAI-compatible but has quirks: JSON mode can return empty, streaming uses SSE format
  - Cache hit pricing is 10x cheaper — the system prompt prefix must be constant across calls to maximize hits

  **Acceptance Criteria**:
  - [ ] Test files: `backend/tests/test_ai_provider.py`
  - [ ] `cd backend && pytest tests/test_ai_provider.py` → PASS (4+ tests)
  - [ ] All practice problem outputs contain warning disclaimer

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Concept extraction returns relevant keywords
    Tool: Bash (pytest)
    Preconditions: Backend tests configured with mocked httpx responses
    Steps:
      1. Run: cd backend && pytest tests/test_ai_provider.py::test_concept_extraction -v
      2. Test sends 'Explain how Y(z) = 0.5z/(z-0.8) works' to extract_concepts()
      3. Mock returns ["Z-transform", "discrete transfer function"]
      4. Assert returned list contains expected concepts
    Expected Result: Test passes, concepts list matches mock
    Failure Indicators: Test fails, concepts empty, wrong types
    Evidence: .sisyphus/evidence/task-5-concept-extraction.txt

  Scenario: Classification retry on empty response
    Tool: Bash (pytest)
    Preconditions: Mocked httpx that returns empty on first call, valid JSON on second
    Steps:
      1. Run: cd backend && pytest tests/test_ai_provider.py::test_retry_on_empty -v
      2. Verify retry was triggered (mock called twice)
    Expected Result: Test passes, second call succeeds
    Failure Indicators: No retry attempted, exception raised on first empty response
    Evidence: .sisyphus/evidence/task-5-retry-logic.txt
  ```

  **Commit**: YES (groups with T2-T4, T6-T7)
  - Message: `feat(ai): DeepSeek provider abstraction — concept extraction, classification, explanation, practice problems`
  - Files: `backend/app/services/ai_provider.py`, `backend/app/services/deepseek_provider.py`, `backend/app/models/ai_models.py`, `backend/tests/test_ai_provider.py`
  - Pre-commit: `cd backend && pytest tests/test_ai_provider.py`

---

- [x] 6. Description Schema Definition — .md Format Specification

  **What to do**:
  - Create `backend/app/models/description_schema.py` — Pydantic model defining the .md description format:
    ```
    class ChapterDescription:
      source_textbook: str          # Textbook filename/ID
      chapter_number: str            # e.g. "3" or "3.2"
      chapter_title: str             # e.g. "The Z-Transform"
      page_range: tuple[int, int]    # Start and end pages
      summary: str                   # 2-5 sentence summary
      key_concepts: list[ConceptEntry]  # Each with name, classification (EXPLAINS|USES), description
      prerequisites: list[str]       # Concepts reader should already know
      mathematical_content: list[str] # Key equations/theorems described in text
      has_figures: bool              # Whether chapter contains important figures/graphs
      figure_descriptions: list[str]  # Brief description of each key figure
    ```
  - Create `backend/app/services/description_manager.py` — Service to:
    - Serialize ChapterDescription to .md format (structured, keyword-searchable)
    - Parse .md files back to ChapterDescription objects
    - List all descriptions for a textbook / course / math library
    - The .md output format must clearly tag EXPLAINS vs USES per concept
  - The .md format must be designed for efficient keyword search (Step 1):
    - Key concepts listed with explicit EXPLAINS/USES tags
    - Equations described with common names (not just LaTeX)
    - Both formal name ("Z-transform") and common aliases ("z transform", "ZT")
  - TDD: Test serialization round-trip (model → .md → model)
  - TDD: Test that keyword search on the .md text finds expected concepts
  - Create an example description .md file for reference

  **Must NOT do**:
  - Do not generate descriptions from actual PDFs — that's Task 10
  - Do not implement search logic — that's Task 14

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Data model + serialization — straightforward Pydantic work
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4, 5, 7)
  - **Blocks**: Tasks 10, 14
  - **Blocked By**: Task 1

  **References**:

  **WHY This Task Matters**:
  - The description schema is the CONTRACT between document processing (Task 10), keyword search (Task 14), and AI categorization (Task 15).
  - If the schema is wrong, everything downstream breaks. Define it once, correctly, first.

  **Acceptance Criteria**:
  - [ ] `backend/tests/test_description_schema.py` → PASS
  - [ ] Example .md file exists and is parseable back to model
  - [ ] .md format includes EXPLAINS/USES tags that are grep-able

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Description .md roundtrip preserves all fields
    Tool: Bash (pytest)
    Steps:
      1. Create a ChapterDescription with all fields populated
      2. Serialize to .md string
      3. Parse .md string back to ChapterDescription
      4. Assert all fields match original
    Expected Result: All fields preserved through serialization cycle
    Evidence: .sisyphus/evidence/task-6-roundtrip.txt

  Scenario: Keyword search finds EXPLAINS tagged concepts
    Tool: Bash (pytest)
    Steps:
      1. Create .md with concept 'Z-transform' tagged EXPLAINS
      2. Search .md text for 'Z-transform'
      3. Verify match found and tagged as EXPLAINS
    Expected Result: Search returns hit with correct EXPLAINS classification
    Evidence: .sisyphus/evidence/task-6-keyword-search.txt
  ```

  **Commit**: YES (groups with T2-T5, T7)
  - Message: `feat(schema): description .md format spec with EXPLAINS/USES taxonomy`
  - Files: `backend/app/models/description_schema.py`, `backend/app/services/description_manager.py`
  - Pre-commit: `cd backend && pytest tests/test_description_schema.py`

---

- [x] 7. SQLite Metadata Store + Filesystem Layout

  **What to do**:
  - Create `backend/app/services/storage.py` — SQLite-based metadata store:
    - Tables: `textbooks` (id, title, filepath, course, library_type[math|course], processed_at)
    - Tables: `chapters` (id, textbook_id, chapter_number, title, page_start, page_end, description_path)
    - Tables: `courses` (id, name, created_at)
    - Tables: `conversations` (id, course_id, query, created_at) + `messages` (id, conversation_id, role, content)
    - Use aiosqlite for async operations
  - Create `backend/app/services/filesystem.py` — Manages the data directory layout:
    - `{DATA_DIR}/textbooks/{textbook_id}/original.pdf` — Original file
    - `{DATA_DIR}/textbooks/{textbook_id}/images/` — Extracted images
    - `{DATA_DIR}/textbooks/{textbook_id}/chapters/{chapter_num}.txt` — Extracted text per chapter
    - `{DATA_DIR}/descriptions/{textbook_id}/{chapter_num}.md` — Generated descriptions
    - `{DATA_DIR}/descriptions/math_library/` — Math library descriptions (always available)
    - `{DATA_DIR}/descriptions/{course_name}/` — Course-specific descriptions
  - TDD: Test creating a textbook record and retrieving it
  - TDD: Test filesystem layout creation for a new textbook

  **Must NOT do**:
  - Do not use any ORM (SQLAlchemy etc) — keep it simple with raw SQL + aiosqlite
  - Do not implement conversation history logic — just the schema

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Standard SQLite setup + filesystem operations
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4, 5, 6)
  - **Blocks**: Tasks 8, 9
  - **Blocked By**: Task 1

  **References**:

  **External References**:
  - aiosqlite: `https://aiosqlite.omnilib.dev/` — Async SQLite for FastAPI

  **Acceptance Criteria**:
  - [ ] `backend/tests/test_storage.py` → PASS
  - [ ] SQLite DB created with correct schema on first run
  - [ ] Filesystem directories created for a test textbook

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Textbook record CRUD operations work
    Tool: Bash (pytest)
    Steps:
      1. Create a textbook record with title, filepath, course
      2. Retrieve by ID, verify all fields
      3. List textbooks for a course, verify count
    Expected Result: All CRUD operations succeed with correct data
    Evidence: .sisyphus/evidence/task-7-sqlite-crud.txt
  ```

  **Commit**: YES (groups with T2-T6)
  - Message: `feat(storage): SQLite metadata store + filesystem layout manager`
  - Files: `backend/app/services/storage.py`, `backend/app/services/filesystem.py`
  - Pre-commit: `cd backend && pytest tests/test_storage.py`

---

- [x] 8. PDF Parser — Text + Image + TOC Extraction

  **What to do**:
  - Create `backend/app/services/pdf_parser.py` using PyMuPDF:
    - `async def parse_pdf(filepath: str) -> ParsedDocument`
    - Extract text page-by-page using `page.get_text('text')`. Store per-page text.
    - Extract TOC using `doc.get_toc()`. Map each entry to (level, title, page_number).
    - If TOC is empty (no bookmarks): use AI fallback — send first 3 pages to DeepSeek, ask it to identify the table of contents structure. Parse AI response into chapter list.
    - Extract images using `page.get_images()` + `doc.extract_image()`. Save as PNG to filesystem.
    - For each image: record which page it came from + image index for later display.
    - Split document text into chapters based on TOC page ranges.
    - Save extracted text per chapter to `{DATA_DIR}/textbooks/{id}/chapters/{num}.txt`
    - Save images to `{DATA_DIR}/textbooks/{id}/images/page{N}_img{M}.png`
    - Register textbook + chapters in SQLite via storage service (Task 7)
  - Create FastAPI endpoint: `POST /api/textbooks/import` — accepts file upload, triggers processing
  - Create FastAPI endpoint: `GET /api/textbooks/{id}/status` — returns processing progress
  - TDD: Test TOC extraction on actual simulation material textbook
  - TDD: Test chapter text splitting based on TOC page ranges
  - TDD: Test image extraction produces files
  - TDD: Test empty TOC triggers AI fallback path

  **Must NOT do**:
  - Do not generate descriptions — that's Task 10
  - Do not implement PPT/DOCX parsing — that's Task 9

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex file processing with multiple extraction paths, AI fallback, and real PDF testing
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 9, 10, 11, 12)
  - **Blocks**: Tasks 10, 24, 25
  - **Blocked By**: Tasks 2, 7

  **References**:

  **Pattern References**:
  - `Simulation Material/Textbook/DigitalControlSystems-NeweditionI.D.LandauG.Zito.pdf` — Real textbook for testing
  - `Simulation Material/University Material/[Lecture 1]*.pdf` — Lecture slides (different PDF structure) for testing
  - Task 1 spike_report.md — Contains findings on equation quality, TOC availability, image extraction results

  **External References**:
  - PyMuPDF: `https://pymupdf.readthedocs.io/en/latest/` — get_text, get_toc, get_images, extract_image

  **Acceptance Criteria**:
  - [ ] `backend/tests/test_pdf_parser.py` → PASS (4+ tests)
  - [ ] `POST /api/textbooks/import` with test PDF returns 200 + job ID
  - [ ] After processing: chapter text files exist, images extracted, DB records created

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Import real textbook end-to-end
    Tool: Bash (curl + file checks)
    Preconditions: Backend running, textbook PDF at Simulation Material/Textbook/
    Steps:
      1. curl -X POST http://localhost:8000/api/textbooks/import -F 'file=@Simulation Material/Textbook/DigitalControlSystems-NeweditionI.D.LandauG.Zito.pdf'
      2. Poll GET /api/textbooks/{id}/status until complete
      3. Check: ls {DATA_DIR}/textbooks/{id}/chapters/ — verify .txt files exist
      4. Check: ls {DATA_DIR}/textbooks/{id}/images/ — verify .png files exist
    Expected Result: Multiple chapter .txt files, multiple image .png files, DB records created
    Failure Indicators: Empty directories, 500 errors, no DB records
    Evidence: .sisyphus/evidence/task-8-pdf-import.txt

  Scenario: PDF without bookmarks triggers AI TOC fallback
    Tool: Bash (pytest with mock)
    Steps:
      1. Provide a PDF with empty get_toc() result
      2. Verify AI fallback is called (DeepSeek asked to identify chapters)
      3. Verify chapters are still created from AI response
    Expected Result: Chapters extracted via AI analysis even without bookmarks
    Evidence: .sisyphus/evidence/task-8-toc-fallback.txt
  ```

  **Commit**: YES
  - Message: `feat(parser): PDF text + image + TOC extraction with AI fallback`
  - Files: `backend/app/services/pdf_parser.py`, `backend/app/routers/textbooks.py`
  - Pre-commit: `cd backend && pytest tests/test_pdf_parser.py`

---

- [x] 9. PPT/DOCX Parser — Slide and Paragraph Extraction

  **What to do**:
  - Create `backend/app/services/pptx_parser.py` using python-pptx:
    - Extract text slide-by-slide: `slide.shapes[].text` with slide number tracking
    - Extract images from slides: iterate shapes, save images
    - Output: list of `{slide_number, text, image_paths}`
  - Create `backend/app/services/docx_parser.py` using python-docx:
    - Extract text paragraph-by-paragraph with heading detection
    - Extract images from document
    - Output: list of `{section, text, heading_level, image_paths}`
  - Create unified `backend/app/services/document_parser.py` — dispatcher:
    - Detects file type by extension (.pdf, .pptx, .docx)
    - Routes to appropriate parser
    - Returns common `ParsedDocument` model
  - Add to existing import endpoint: support .pptx and .docx uploads alongside .pdf
  - TDD: Test PPTX parsing preserves slide numbers
  - TDD: Test DOCX parsing detects headings

  **Must NOT do**:
  - Do not support .ppt or .doc (legacy formats) — only .pptx and .docx

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Multiple parsers with image extraction — moderate complexity
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 8, 10, 11, 12)
  - **Blocks**: Task 25
  - **Blocked By**: Tasks 2, 7

  **References**:

  **External References**:
  - python-pptx: `https://python-pptx.readthedocs.io/` — Presentation, Slide, Shape objects
  - python-docx: `https://python-docx.readthedocs.io/` — Document, Paragraph, Run objects

  **Acceptance Criteria**:
  - [ ] `backend/tests/test_pptx_parser.py` + `test_docx_parser.py` → PASS
  - [ ] Slide numbers preserved in PPTX output

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: PPTX parsing preserves per-slide text with numbers
    Tool: Bash (pytest)
    Steps:
      1. Create a test .pptx with 3 slides, each with known text
      2. Parse and verify slide 1 text = expected, slide 2 text = expected, etc.
    Expected Result: Each slide's text extracted with correct slide number
    Evidence: .sisyphus/evidence/task-9-pptx-parse.txt
  ```

  **Commit**: YES
  - Message: `feat(parser): PPT/DOCX text + image extraction with unified dispatcher`
  - Files: `backend/app/services/pptx_parser.py`, `backend/app/services/docx_parser.py`, `backend/app/services/document_parser.py`
  - Pre-commit: `cd backend && pytest tests/test_pptx_parser.py tests/test_docx_parser.py`

---

- [x] 10. AI Description Generator — Chapter/Subchapter .md Files

  **What to do**:
  - Create `backend/app/services/description_generator.py`:
    - Takes extracted chapter text (from Task 8) + chapter metadata
    - Sends chapter text to DeepSeek (deepseek-chat) with a carefully crafted prompt:
      - "Read this chapter and generate a structured description following this exact schema: [schema from Task 6]"
      - "For each concept mentioned, classify whether this chapter EXPLAINS the concept (introduces, derives, defines) or USES the concept (applies it in examples, problems, design)"
      - "List all mathematical equations/theorems by their common names"
      - "Note whether important figures/graphs are present and describe them"
    - Parses AI response into ChapterDescription model (Task 6)
    - Saves as .md file using description_manager (Task 6)
    - Handles chapters that are too long for context: splits into sections, generates per-section descriptions, then merges
    - For the math library: descriptions should include common aliases and related concepts
  - Create FastAPI endpoint: `POST /api/textbooks/{id}/generate-descriptions`
  - Create FastAPI endpoint: `GET /api/textbooks/{id}/descriptions` — list all generated descriptions
  - System prompt must be constant across calls for DeepSeek cache hit optimization
  - Process chapters sequentially (not parallel) to avoid rate limiting + ensure cache hits
  - TDD: Test prompt construction includes schema format
  - TDD: Test AI response parsing to ChapterDescription
  - TDD: Test long chapter splitting strategy

  **Must NOT do**:
  - Do not use embeddings or vector DB — descriptions are plain .md files on disk
  - Do not generate descriptions for images — text-only descriptions (unless OpenAI vision available, Task 12)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Prompt engineering + response parsing + chunking strategy requires careful design
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 8, 9, 11, 12)
  - **Blocks**: Tasks 14, 25, 26
  - **Blocked By**: Tasks 5, 6, 8

  **References**:

  **Pattern References**:
  - Task 6 description schema — The exact .md format descriptions must follow
  - Task 5 AI provider — Use deepseek_provider.chat() for generation
  - Task 8 parsed output — Chapter text files that serve as input to description generation

  **Acceptance Criteria**:
  - [ ] `backend/tests/test_description_generator.py` → PASS
  - [ ] Generated .md files follow Task 6 schema exactly
  - [ ] EXPLAINS/USES tags present for each key concept
  - [ ] Long chapters are split and merged correctly

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Generate description for a real textbook chapter
    Tool: Bash (curl)
    Preconditions: Textbook imported (Task 8), backend running
    Steps:
      1. POST /api/textbooks/{id}/generate-descriptions
      2. Wait for completion
      3. GET /api/textbooks/{id}/descriptions — verify .md files listed
      4. Read one .md file — verify contains Summary, Key Concepts, EXPLAINS/USES tags
    Expected Result: .md descriptions generated for all chapters with correct schema
    Failure Indicators: Empty descriptions, missing EXPLAINS/USES, schema violations
    Evidence: .sisyphus/evidence/task-10-generated-description.md

  Scenario: Long chapter is split before sending to AI
    Tool: Bash (pytest)
    Steps:
      1. Provide chapter text > 100K tokens
      2. Verify it's split into sections before AI call
      3. Verify merged description covers all sections
    Expected Result: All sections represented in final description
    Evidence: .sisyphus/evidence/task-10-long-chapter.txt
  ```

  **Commit**: YES
  - Message: `feat(descriptions): AI-powered chapter/subchapter .md description generator`
  - Files: `backend/app/services/description_generator.py`, `backend/app/routers/descriptions.py`
  - Pre-commit: `cd backend && pytest tests/test_description_generator.py`

---

- [x] 11. Pixel Art Design System — Theme Tokens, Fonts, Base Components

  **What to do**:
  - Create `frontend/src/styles/` design system:
    - `theme.css` — CSS custom properties for the pixel art theme:
      - Colors: dark background (#1a1a2e), accent colors inspired by Stardew Valley/Celeste palette
      - Font: 'Press Start 2P' for UI chrome (buttons, labels, titles)
      - Font: 'Inter' or 'JetBrains Mono' for content text (readable, not pixelated)
      - Font: KaTeX fonts for equations (already provided by KaTeX)
      - Border style: pixel art borders (2-4px solid, no border-radius OR stepped pixel corners)
      - Spacing: 8px grid system (pixel-perfect alignment)
    - `pixel-components.css` — Base component styles:
      - Buttons (chunky, pixel-styled with hover states)
      - Input fields (pixel border, retro feel)
      - Dialog/modal (RPG-style text box with pixel border)
      - Scrollbars (custom pixel-styled)
      - Loading spinner (pixel art animation)
    - `content-area.css` — Styles for content rendering area:
      - Clean, readable typography for equations and text
      - NO pixel art inside content areas — high-fidelity rendering
      - Image display: proper scaling, borders, captions
  - Create base React components:
    - `PixelButton` — with variant (primary, secondary, danger)
    - `PixelPanel` — container with pixel art border
    - `PixelInput` — text input / textarea
    - `PixelBadge` — for EXPLAINS/USES tags (green for EXPLAINS, blue for USES)
    - `PixelDialog` — modal/dialog with RPG text box style
  - CRITICAL: Import 'Press Start 2P' from Google Fonts. Use it ONLY for UI elements, NEVER for content.
  - TDD: Test each component renders without errors
  - TDD: Test PixelBadge renders correct text and color for EXPLAINS vs USES

  **Must NOT do**:
  - Do not create custom pixel art sprites/assets — CSS-only theming for now
  - Do not apply pixel fonts to content areas — equations and text must be readable
  - Do not build page layouts — that's Tasks 16-17

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Design system creation requiring visual taste and CSS expertise
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Needed for design token creation, component styling, visual harmony

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 8, 9, 10, 12)
  - **Blocks**: Tasks 16, 17, 22, 23, 24, 28, 29
  - **Blocked By**: Task 3

  **References**:

  **External References**:
  - NES.css: `https://nostalgic-css.github.io/NES.css/` — Reference for pixel border patterns and component styling
  - 8bitcn/ui: `https://github.com/TheOrcDev/8bitcn-ui` — Modern 8-bit React components as inspiration
  - Press Start 2P font: `https://fonts.google.com/specimen/Press+Start+2P`
  - Celeste color palette references — modern pixel art colors

  **Acceptance Criteria**:
  - [ ] `frontend/src/__tests__/pixel-components.test.tsx` → PASS
  - [ ] All 5 base components render correctly
  - [ ] Press Start 2P font loads and applies to UI elements only
  - [ ] Content areas use readable (non-pixel) fonts

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Pixel components render with correct styling
    Tool: Playwright
    Preconditions: Frontend dev server running
    Steps:
      1. Navigate to http://localhost:5173
      2. Render a test page with all 5 components
      3. Screenshot each component
      4. Verify PixelBadge with 'EXPLAINS' has green styling
      5. Verify PixelBadge with 'USES' has blue styling
      6. Verify text inside PixelPanel uses readable font (not Press Start 2P)
    Expected Result: All components visible with pixel art styling, badges correctly colored
    Failure Indicators: Missing borders, wrong fonts in content area, badge colors swapped
    Evidence: .sisyphus/evidence/task-11-pixel-components.png
  ```

  **Commit**: YES
  - Message: `feat(ui): pixel art design system — theme tokens, fonts, 5 base components`
  - Files: `frontend/src/styles/**`, `frontend/src/components/pixel/**`
  - Pre-commit: `cd frontend && npx vitest run`

---

- [x] 12. OpenAI Vision Provider (Optional) — Behind Same Abstraction

  **What to do**:
  - Create `backend/app/services/openai_provider.py` implementing the same AI provider interface (Task 5):
    - Uses httpx to call OpenAI API with GPT-4o model
    - Implements `analyze_image(image_path: str, prompt: str) -> str` — sends image + question to GPT-4o Vision
    - Implements all other interface methods by delegating to OpenAI chat API
    - API key read from config (optional — app works without it)
  - Create `backend/app/services/ai_router.py` — smart router:
    - For text tasks: always use DeepSeek (cheaper)
    - For vision tasks: use OpenAI if available, otherwise return 'Vision not available' message
    - Configuration: user can set preferred provider in settings
  - TDD: Test that missing OpenAI key gracefully falls back
  - TDD: Test image analysis call structure (mocked)

  **Must NOT do**:
  - Do not make OpenAI required — must be fully optional
  - Do not use OpenAI for text tasks — DeepSeek is cheaper and primary

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple API client following existing pattern from Task 5
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 8, 9, 10, 11)
  - **Blocks**: None
  - **Blocked By**: Task 5

  **References**:

  **Pattern References**:
  - Task 5 `ai_provider.py` — Base class to implement. Follow exact same interface.

  **External References**:
  - OpenAI Vision API: `https://platform.openai.com/docs/guides/vision` — Image input format for GPT-4o

  **Acceptance Criteria**:
  - [ ] `backend/tests/test_openai_provider.py` → PASS
  - [ ] App starts and functions without OpenAI key configured

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: App works without OpenAI key
    Tool: Bash
    Steps:
      1. Start backend WITHOUT OPENAI_API_KEY env var
      2. curl GET /health — verify 200
      3. curl POST /api/textbooks/import — verify works (uses DeepSeek only)
    Expected Result: All non-vision features work without OpenAI
    Evidence: .sisyphus/evidence/task-12-no-openai.txt
  ```

  **Commit**: YES
  - Message: `feat(ai): OpenAI vision provider (optional) with smart routing`
  - Files: `backend/app/services/openai_provider.py`, `backend/app/services/ai_router.py`
  - Pre-commit: `cd backend && pytest tests/test_openai_provider.py`

---

- [x] 13. Step 0 — AI Concept and Equation Form Extractor

  **What to do**:
  - Create `backend/app/services/concept_extractor.py`:
    - `async def extract_concepts(query: str) -> ConceptExtraction`
    - Sends user's question to DeepSeek (deepseek-chat) with prompt:
      - "Analyze this student's question. Identify: 1) Named concepts/theorems/transforms mentioned explicitly (e.g., 'Z-transform', 'Laplace'). 2) Concepts IMPLIED by equations even if not named — recognize equation FORMS regardless of specific variable values. E.g., Y(z)=az/(z-b) is a Z-transform expression. 3) Related prerequisite concepts that may help understand this topic. Return as JSON."
    - Recognizes equation forms: user writes Y(z)=0.5z/(z-0.8) → extractor identifies this as Z-transform even though values differ from textbook
    - Returns both explicit keywords (for Step 1 Ctrl+F) and inferred concepts (for broader search)
    - Also returns suggested search terms: formal name + common aliases + related terms
  - Create FastAPI endpoint: `POST /api/search/extract-concepts` — takes query string, returns ConceptExtraction
  - Use deepseek-chat model (cheap, small output needed)
  - TDD: Test with literal concept mention ('explain the Z-transform') → extracts 'Z-transform'
  - TDD: Test with equation-only input ('solve Y(z)=0.5z/(z-0.8)') → infers 'Z-transform'
  - TDD: Test with vague input ('explain this equation for discrete systems') → suggests related terms

  **Must NOT do**:
  - Do not implement keyword search — that's Task 14
  - Do not use embeddings

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Prompt engineering for equation form recognition requires iterative testing
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 14, 15, 16, 17, 18)
  - **Blocks**: None (output feeds into Task 14 at runtime, not build-time)
  - **Blocked By**: Task 5

  **References**:

  **Pattern References**:
  - Task 5 `deepseek_provider.py` — Use the chat() method with deepseek-chat model
  - Task 5 `ConceptExtraction` Pydantic model — Return type

  **Acceptance Criteria**:
  - [ ] `backend/tests/test_concept_extractor.py` → PASS (3+ tests)
  - [ ] Equation form recognition works for Z-transform, Laplace, Fourier examples

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Equation form recognition identifies Z-transform from values
    Tool: Bash (curl)
    Preconditions: Backend running with DeepSeek API key
    Steps:
      1. POST /api/search/extract-concepts with body {"query": "How do I solve Y(z) = 0.5z/(z-0.8)?"}
      2. Parse JSON response
      3. Verify 'concepts' array contains 'Z-transform' or 'z-transform'
    Expected Result: Z-transform identified even though not explicitly named in query
    Failure Indicators: Empty concepts, only generic terms like 'equation', timeout
    Evidence: .sisyphus/evidence/task-13-equation-recognition.json

  Scenario: Explicit concept extraction
    Tool: Bash (curl)
    Steps:
      1. POST /api/search/extract-concepts with {"query": "Explain the Fourier transform and its applications"}
      2. Verify 'concepts' contains 'Fourier transform'
      3. Verify 'related_terms' includes aliases like 'FT', 'DFT', 'frequency domain'
    Expected Result: Explicit concept found + related terms suggested
    Evidence: .sisyphus/evidence/task-13-explicit-concepts.json
  ```

  **Commit**: YES
  - Message: `feat(search): AI concept/equation form extractor — Step 0 of hybrid search`
  - Files: `backend/app/services/concept_extractor.py`, `backend/app/routers/search.py`
  - Pre-commit: `cd backend && pytest tests/test_concept_extractor.py`

---

- [x] 14. Step 1 — Keyword Search Engine Across Descriptions

  **What to do**:
  - Create `backend/app/services/keyword_search.py`:
    - `def search_descriptions(keywords: list[str], library_type: str|None = None) -> list[SearchHit]`
    - Scans all .md description files in `{DATA_DIR}/descriptions/`
    - For each keyword: case-insensitive text search (like Ctrl+F) across all .md files
    - Returns matches with: file path, matched keyword, surrounding context (2-3 lines), source textbook, chapter info
    - Searches BOTH math library + course-specific descriptions simultaneously
    - Supports filtering by library_type ('math' or 'course' or None for both)
    - Performance: reads all .md files into memory on startup (they're small), refreshes on new description generation
    - Handles common aliases: search for 'z-transform' also searches 'z transform', 'ZT', 'z-domain'
  - Create FastAPI endpoint: `POST /api/search/keyword` — takes keywords list, returns SearchHit list
  - TDD: Test search finds exact keyword match
  - TDD: Test search finds alias match
  - TDD: Test search across multiple textbooks returns results from each
  - TDD: Test empty results for non-existent concept

  **Must NOT do**:
  - Do not use any vector DB or embeddings — this is pure text search
  - Do not use AI for this step — it's meant to be free and fast

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Text search with alias handling and performance considerations
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 13, 15, 16, 17, 18)
  - **Blocks**: Tasks 15, 22
  - **Blocked By**: Tasks 6, 10

  **References**:

  **Pattern References**:
  - Task 6 description schema — .md format to search through. EXPLAINS/USES tags are in the text.
  - Task 7 filesystem layout — Where descriptions are stored on disk

  **Acceptance Criteria**:
  - [ ] `backend/tests/test_keyword_search.py` → PASS (4+ tests)
  - [ ] Search completes in < 100ms for typical description set

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Keyword search finds Z-transform across multiple textbooks
    Tool: Bash (curl)
    Preconditions: Descriptions generated for test textbook (Task 10 complete)
    Steps:
      1. POST /api/search/keyword with {"keywords": ["Z-transform"]}
      2. Verify response contains 1+ SearchHit objects
      3. Each hit has: file_path, matched_keyword, context_snippet, source_textbook, chapter
    Expected Result: At least 1 hit from the test textbook with surrounding context
    Failure Indicators: Empty results, missing context, wrong chapter attribution
    Evidence: .sisyphus/evidence/task-14-keyword-search.json
  ```

  **Commit**: YES
  - Message: `feat(search): keyword search engine — Step 1 of hybrid search`
  - Files: `backend/app/services/keyword_search.py`
  - Pre-commit: `cd backend && pytest tests/test_keyword_search.py`

---

- [x] 15. Step 2 — AI Categorization: EXPLAINS vs USES

  **What to do**:
  - Create `backend/app/services/match_categorizer.py`:
    - `async def categorize_matches(matches: list[SearchHit], concept: str) -> list[ClassifiedMatch]`
    - Takes keyword search results (Task 14 output) + the original concept
    - Sends ONLY the matched descriptions (not all descriptions) to DeepSeek (deepseek-chat)
    - Prompt: "For each chapter description below, classify whether the chapter EXPLAINS [concept] (introduces, derives, defines, proves it) or USES [concept] (applies it in examples, problems, further topics). Rate confidence 0-1. Be precise: a chapter that has one equation using Z-transform but is mainly about stability analysis should be classified as USES, not EXPLAINS."
    - Returns ClassifiedMatch objects with EXPLAINS/USES tags + confidence + brief reason
    - Sort results: EXPLAINS first (students usually want explanations), then USES, both by confidence desc
    - Uses JSON mode for structured output with retry logic (from Task 5)
  - Create FastAPI endpoint: `POST /api/search/categorize` — takes matches + concept, returns categorized list
  - Combine Steps 0-2 into a single orchestrated endpoint: `POST /api/search/query`
    - Takes user's raw query → extract_concepts → keyword_search → categorize → return categorized results
  - TDD: Test categorization sorts EXPLAINS before USES
  - TDD: Test confidence thresholding (filter out < 0.3 confidence)
  - TDD: Test the full query pipeline (Steps 0+1+2 combined)

  **Must NOT do**:
  - Do not read actual chapter content here — only descriptions. Content reading is Step 4 (Task 19)
  - Do not use embeddings

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Prompt engineering + orchestration of multi-step pipeline
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 13, 14, 16, 17, 18)
  - **Blocks**: Tasks 19, 22
  - **Blocked By**: Tasks 5, 14

  **References**:

  **Pattern References**:
  - Task 5 `ClassifiedMatch` model — Return type with EXPLAINS/USES enum
  - Task 14 keyword search — Provides input matches to categorize
  - Task 13 concept extractor — Provides concept + keywords for the pipeline

  **Acceptance Criteria**:
  - [ ] `backend/tests/test_match_categorizer.py` → PASS
  - [ ] EXPLAINS results sorted before USES results
  - [ ] Full pipeline endpoint `/api/search/query` works end-to-end

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full search pipeline from query to categorized results
    Tool: Bash (curl)
    Preconditions: Descriptions generated, backend running
    Steps:
      1. POST /api/search/query with {"query": "Explain the Z-transform and its derivation"}
      2. Verify response contains categorized matches
      3. Verify at least one match tagged 'EXPLAINS'
      4. Verify EXPLAINS matches appear before USES matches in the list
    Expected Result: Categorized results with EXPLAINS/USES tags, sorted correctly
    Failure Indicators: All tagged same way, no EXPLAINS found, empty results
    Evidence: .sisyphus/evidence/task-15-full-pipeline.json
  ```

  **Commit**: YES
  - Message: `feat(search): AI categorization EXPLAINS/USES — Step 2 + full search pipeline`
  - Files: `backend/app/services/match_categorizer.py`, `backend/app/routers/search.py` (updated)
  - Pre-commit: `cd backend && pytest tests/test_match_categorizer.py`

---

- [x] 16. Bookshelf View — Course Grid + Book Selection

  **What to do**:
  - Create `frontend/src/pages/BookshelfPage.tsx`:
    - Grid of pixel art book spines, each representing a course/textbook
    - Each book shows: title (shortened), course name, number of chapters
    - Click a book → navigates to Desk view (Task 17) for that textbook
    - Books have idle animation (subtle pixel shimmer or floating particles)
    - Include a Math Library shelf section (always visible, separate from course books)
    - '+' button to import new textbook (triggers file dialog → upload to backend)
  - Create `frontend/src/api/textbooks.ts` — API client:
    - `getTextbooks(): Promise<Textbook[]>`
    - `importTextbook(file: File): Promise<ImportJob>`
    - `getImportStatus(jobId: string): Promise<ImportStatus>`
  - Use React Router for navigation between Bookshelf → Desk
  - TDD: Test BookshelfPage renders textbook list from API response
  - TDD: Test clicking a book navigates to desk route

  **Must NOT do**:
  - Do not create custom sprite assets — CSS-only pixel art for books
  - Do not implement Desk view — that's Task 17

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Pixel art visual styling + layout design
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 13, 14, 15, 17, 18)
  - **Blocks**: None
  - **Blocked By**: Task 11

  **References**:

  **Pattern References**:
  - Task 11 pixel components — Use PixelPanel, PixelButton from the design system

  **Acceptance Criteria**:
  - [ ] `frontend/src/__tests__/BookshelfPage.test.tsx` → PASS
  - [ ] Books render as pixel art styled grid items

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Bookshelf displays imported textbooks
    Tool: Playwright
    Steps:
      1. Navigate to http://localhost:5173/
      2. Verify bookshelf page renders with at least 1 book (from imported test data)
      3. Verify book shows title text
      4. Click the book
      5. Verify URL changes to /desk/{textbookId}
    Expected Result: Bookshelf with clickable pixel art books, navigation works
    Evidence: .sisyphus/evidence/task-16-bookshelf.png
  ```

  **Commit**: YES
  - Message: `feat(ui): pixel art bookshelf view with course grid`
  - Files: `frontend/src/pages/BookshelfPage.tsx`, `frontend/src/api/textbooks.ts`
  - Pre-commit: `cd frontend && npx vitest run`

---

- [x] 17. Desk View — Four-Column Layout with Panel Swapping, Merge, and Image Pinning

  **What to do**:
  - Create `frontend/src/pages/DeskPage.tsx` — the main study workspace:
    - **Four-column layout**:
      - **Left (~15%)**: Input column
        - Query input (PixelInput) at top
        - Action buttons row (always visible, prominent pixel-styled):
          - [Explain] — pre-fills 'Explain [current topic]'
          - [Derive] — pre-fills 'Derive [current topic] step by step'
          - [Example] — pre-fills 'Show me a worked example of [current topic]'
          - [Generate Q&A] — prominent button, calls /api/practice directly with current context. Generates practice questions + solutions in Panel A/B with difficulty selector (Easy/Medium/Hard)
          - Buttons are context-aware: [current topic] auto-fills from last search or active concept
        - Conversation/chat history below (scrollable, newest at bottom)
        - User messages styled right-aligned, AI responses left-aligned, pixel art chat bubbles
      - **Panel A (~35%)**: Primary content panel — can display AI explanation OR raw textbook
      - **Panel B (~35%)**: Secondary content panel — displays the other content type
      - **Quick Ref (~15%)**: Always-visible sidebar
        - Pinned formula tables (Z-transform table, Laplace pairs, etc.)
        - Common quick questions ('derive Z-TF', 'what is DF2', 'ROC definition')
        - Recently viewed concepts
        - Pinned images as thumbnail icons (drag from textbook to pin here)
    - **Panel swapping**: [⇄ Swap] button or drag to swap Panel A ↔ Panel B content
    - **Panel merge mode**: Both panels can merge into one wide panel when only one content type is needed. Toggle via button or by dragging the panel divider fully.
    - **Cross-referencing**: Click [Source: Ch.3.2] citation in AI panel → instantly loads that chapter in the OTHER panel
    - **ESC navigation**: ESC always goes back one level (equation detail → panel, fullscreen → normal, desk → bookshelf). Global keydown listener.
    - **Image drag & pin**:
      - Any image in textbook view can be dragged out as a floating overlay (stays visible while scrolling)
      - Drag image to Quick Ref column → collapses into thumbnail icon. Click icon → expands.
      - Floating images have close button + opacity slider
    - Back button (← bookshelf) in top-left + ESC shortcut
  - Create `frontend/src/hooks/useConversation.ts` — manages chat state:
    - Message list (user + AI messages)
    - Send message function (calls backend API)
    - Loading state while AI responds
  - Create `frontend/src/hooks/usePanelLayout.ts` — manages panel state:
    - Panel A content type (ai | textbook | empty), Panel B content type
    - Swap function, merge/split toggle
    - Active textbook chapter for each panel
  - Create `frontend/src/hooks/usePinnedItems.ts` — manages Quick Ref state:
    - Pinned formulas, pinned images, recent concepts
    - Add/remove pin functions
    - Persist pinned items to localStorage
  - Create `frontend/src/components/FloatingImage.tsx` — draggable image overlay:
    - Absolute positioned, draggable via mouse
    - Close button, opacity control
    - Collapse-to-icon when dragged to Quick Ref
  - TDD: Test DeskPage renders four-column layout
  - TDD: Test panel swap changes content types
  - TDD: Test ESC key navigates back
  - TDD: Test useConversation hook manages message state
  - TDD: Test usePinnedItems persists to localStorage

  **Must NOT do**:
  - Do not implement search result display — that's Task 22
  - Do not implement content rendering — that's Task 18/23
  - Do not implement equation hover — that's part of Task 18 (ContentRenderer)
  - Do not connect to real backend — use mock data for layout tests

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Complex four-panel layout with drag interactions, floating elements, merge/split behavior
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Advanced layout + interaction design

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 13, 14, 15, 16, 18)
  - **Blocks**: Tasks 22, 23, 24, 29
  - **Blocked By**: Task 11

  **References**:

  **Pattern References**:
  - Task 11 pixel components — PixelPanel, PixelInput, PixelButton, PixelBadge

  **External References**:
  - react-resizable-panels: `https://github.com/bvaughn/react-resizable-panels` — For panel dividers + merge/split
  - @dnd-kit/core: `https://dndkit.com/` — For image drag-and-drop to Quick Ref

  **Acceptance Criteria**:
  - [ ] `frontend/src/__tests__/DeskPage.test.tsx` → PASS (5+ tests)
  - [ ] Four-column layout renders correctly
  - [ ] Panel swap works
  - [ ] ESC key navigates back
  - [ ] Pinned items persist in localStorage

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Four-column desk layout with panel interactions
    Tool: Playwright
    Steps:
      1. Navigate to http://localhost:5173/desk/test-id
      2. Verify 4 columns visible: input, panel-a, panel-b, quick-ref
      3. Click [⇄ Swap] button
      4. Verify panel content types swapped
      5. Press Escape key
      6. Verify navigation returns to bookshelf
    Expected Result: Four-column layout with working swap and ESC navigation
    Failure Indicators: Panels missing, swap doesn't change content, ESC does nothing
    Evidence: .sisyphus/evidence/task-17-desk-layout.png

  Scenario: Image drag to Quick Ref creates pinned icon
    Tool: Playwright
    Steps:
      1. Open desk view with textbook content in Panel B
      2. Find an image element in the textbook
      3. Drag image to Quick Ref column
      4. Verify thumbnail icon appears in Quick Ref
      5. Click the thumbnail icon
      6. Verify image expands to viewable size
    Expected Result: Image pins as icon, click expands it
    Evidence: .sisyphus/evidence/task-17-image-pin.png
  ```

  **Commit**: YES
  - Message: `feat(ui): four-column desk layout with panel swap, merge, image pinning, ESC navigation`
  - Files: `frontend/src/pages/DeskPage.tsx`, `frontend/src/hooks/useConversation.ts`, `frontend/src/hooks/usePanelLayout.ts`, `frontend/src/hooks/usePinnedItems.ts`, `frontend/src/components/FloatingImage.tsx`
  - Pre-commit: `cd frontend && npx vitest run`
    Expected Result: Split layout with functional chat input and book panel
    Evidence: .sisyphus/evidence/task-17-desk-layout.png
  ```

  **Commit**: YES
  - Message: `feat(ui): desk view — split chat panel + book panel layout`
  - Files: `frontend/src/pages/DeskPage.tsx`, `frontend/src/hooks/useConversation.ts`
  - Pre-commit: `cd frontend && npx vitest run`

---

- [x] 18. KaTeX + Markdown Content Renderer with Image Support

  **What to do**:
  - Create `frontend/src/components/ContentRenderer.tsx`:
    - Takes Markdown + LaTeX string as input (AI responses include equation metadata annotations)
    - Renders using react-markdown + remark-math + rehype-katex pipeline
    - Inline math: `$E = mc^2$` renders inline
    - Display math: `$$\frac{Y(z)}{X(z)} = \frac{az}{z-b}$$` renders as centered block
    - Code blocks render with syntax highlighting
    - **Equation hover identification**: Each rendered equation wrapped in a hover-able container.
      - AI annotates equations with metadata: `<!-- eq:Z-transform -->$$Y(z)=...$$`
      - On hover: tooltip appears identifying the formula ('Z-transform', 'Laplace transform', 'Transfer function')
      - On click: triggers a focused search for that concept (calls concept extractor → search pipeline)
      - Styled: subtle highlight on hover, tooltip uses PixelPanel styling
    - Images: renders `![alt](image-url)` as draggable images (integrate with DeskPage drag-to-pin)
      - Image URLs point to backend: `http://localhost:8000/api/textbooks/{id}/images/{filename}`
      - Images are draggable: user can drag them out of content flow to float or pin to Quick Ref
    - Source citations render as clickable links: `[Source: Digital Control Systems, Ch.3.2]`
      - Click → emits event to DeskPage to load that chapter in the adjacent panel
    - Warning disclaimers render as pixel-styled alert boxes (red border)
  - Create `frontend/src/components/EquationTooltip.tsx` — hover identification component:
    - Shows formula name, brief description, 'Click to explore' prompt
    - Positioned above/below the equation, doesn't block content
    - Dismiss on mouse leave or ESC
  - Create `frontend/src/components/ImageViewer.tsx` — lightbox for images:
    - Click image → full-size overlay with pixel art border
    - Close button (+ ESC to close), zoom in/out
    - Drag handle for moving to floating position or Quick Ref
  - Create FastAPI endpoint: `GET /api/textbooks/{id}/images/{filename}` — serves extracted images
  - TDD: Test ContentRenderer renders LaTeX equation correctly
  - TDD: Test equation hover tooltip appears with correct identification
  - TDD: Test images are rendered with draggable attribute
  - TDD: Test source citation click emits navigation event
  - TDD: Test warning disclaimer renders as alert box

  **Must NOT do**:
  - Do not use MathJax — KaTeX only (10-100x faster)
  - Do not pixelate content area — use readable fonts for equations and text

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Complex rendering pipeline with math + markdown + images
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 13, 14, 15, 16, 17)
  - **Blocks**: Task 23
  - **Blocked By**: Task 3

  **References**:

  **External References**:
  - react-markdown: `https://github.com/remarkjs/react-markdown` — Markdown renderer
  - remark-math + rehype-katex: For LaTeX in Markdown
  - KaTeX: `https://katex.org/docs/supported.html` — Supported LaTeX commands

  **Acceptance Criteria**:
  - [ ] `frontend/src/__tests__/ContentRenderer.test.tsx` → PASS (5+ tests)
  - [ ] LaTeX renders without errors for Z-transform equations
  - [ ] Equation hover tooltip shows correct formula identification
  - [ ] Images are draggable
  - [ ] Source citations are clickable

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: LaTeX equations render correctly in content
    Tool: Playwright
    Steps:
      1. Render ContentRenderer with: '## Z-Transform\n$$Y(z) = \\frac{0.5z}{z - 0.8}$$\nThis is the transfer function.'
      2. Verify .katex element exists in DOM
      3. Verify no KaTeX error elements (.katex-error) present
      4. Screenshot the rendered equation
    Expected Result: Beautiful equation rendering, no error messages
    Evidence: .sisyphus/evidence/task-18-latex-render.png

  Scenario: Warning disclaimer renders as alert
    Tool: Playwright
    Steps:
      1. Render ContentRenderer with: '> ⚠️ **Warning**: AI-generated solutions may contain errors.'
      2. Verify alert-styled element exists with warning text
    Expected Result: Visually distinct warning box in pixel art style
    Evidence: .sisyphus/evidence/task-18-warning-render.png
  ```

  **Commit**: YES
  - Message: `feat(ui): KaTeX + Markdown content renderer with image support`
  - Files: `frontend/src/components/ContentRenderer.tsx`, `frontend/src/components/ImageViewer.tsx`
  - Pre-commit: `cd frontend && npx vitest run`

---

- [ ] 19. Step 4 — AI Explanation Generator with Streaming

  **What to do**:
  - Create `backend/app/services/explanation_generator.py`:
    - `async def generate_explanation(selected_chapters: list[SelectedChapter], query: str) -> AsyncGenerator[str, None]`
    - Takes user-selected subchapters (from Step 3) + original query
    - Reads ACTUAL chapter content from filesystem (the .txt files from Task 8, NOT descriptions)
    - Sends content to DeepSeek (deepseek-reasoner — 64K output, for detailed explanations)
    - System prompt: "You are a STEM tutor. Using the textbook content provided, explain [concept] to the student. Structure your response as: 1) Introduction/Definition, 2) Mathematical derivation with LaTeX, 3) Intuitive explanation, 4) Key properties/theorems, 5) Common applications. After each section, cite the source: [Source: textbook_title, Ch.X.Y, p.N]. Use LaTeX for ALL equations: inline $...$ and display $$...$$. Be thorough but clear."
    - Streams response using SSE (Server-Sent Events)
    - If total content exceeds context window: prioritize EXPLAINS chapters, truncate USES chapters
    - Includes image references from the source chapters when relevant
  - Create FastAPI streaming endpoint: `POST /api/explain` with `StreamingResponse`
    - Accepts: `{chapter_ids: list[str], query: str}`
    - Returns: SSE stream of Markdown+LaTeX chunks
  - TDD: Test explanation includes source citations
  - TDD: Test streaming yields multiple chunks (not single blob)
  - TDD: Test context window overflow handling (content truncation)

  **Must NOT do**:
  - Do not use deepseek-chat for this — must use deepseek-reasoner (64K output for detailed explanations)
  - Do not skip source citations — every section must reference its source chapter

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Streaming implementation + prompt engineering + content prioritization
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 20, 21, 22, 23, 24)
  - **Blocks**: Tasks 20, 21, 23
  - **Blocked By**: Tasks 5, 15

  **References**:

  **Pattern References**:
  - Task 5 `deepseek_provider.py` — streaming implementation
  - Task 8 chapter text files — `{DATA_DIR}/textbooks/{id}/chapters/{num}.txt` — source content to read

  **External References**:
  - FastAPI StreamingResponse: `https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse`
  - SSE format: `data: {chunk}\n\n`

  **Acceptance Criteria**:
  - [ ] `backend/tests/test_explanation_generator.py` → PASS
  - [ ] Streaming endpoint returns progressive chunks
  - [ ] Every explanation section contains [Source: ...] citation

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Streaming explanation with source citations
    Tool: Bash (curl with SSE)
    Preconditions: Textbook imported + descriptions generated
    Steps:
      1. Search for 'Z-transform' via /api/search/query
      2. Select 2 EXPLAINS chapters from results
      3. POST /api/explain with selected chapter IDs + query
      4. Read SSE stream, collect all chunks
      5. Concatenate chunks into full response
      6. Verify response contains '[Source:' citations
      7. Verify response contains LaTeX ($$...$$)
    Expected Result: Streamed explanation with LaTeX equations and source citations
    Failure Indicators: No streaming (single blob), missing citations, no LaTeX
    Evidence: .sisyphus/evidence/task-19-streaming-explanation.md
  ```

  **Commit**: YES
  - Message: `feat(explain): streaming AI explanation generator with source citations`
  - Files: `backend/app/services/explanation_generator.py`, `backend/app/routers/explain.py`
  - Pre-commit: `cd backend && pytest tests/test_explanation_generator.py`

---

- [ ] 20. Practice Question + Solution Generator with Warning

  **What to do**:
  - Create `backend/app/services/practice_generator.py`:
    - `async def generate_practice(content: str, topic: str, difficulty: str, count: int) -> PracticeProblems`
    - Takes textbook content + topic + difficulty (easy/medium/hard) + number of problems
    - Sends to DeepSeek (deepseek-reasoner) with prompt:
      - "Generate {count} practice problems about {topic} at {difficulty} level. For each: 1) State the problem clearly with all given values. 2) Provide step-by-step solution with LaTeX equations. 3) Identify which equations/theorems are used in each step (e.g., 'Applying the Z-transform definition from Ch.3.2'). 4) Include a final answer clearly boxed. Use LaTeX for ALL math."
    - EVERY response MUST include disclaimer: "⚠️ **Warning**: AI-generated solutions may contain calculation errors. Verify your answers independently or cross-check with your textbook."
    - Validates that disclaimer is present before returning (hard fail if missing)
  - Create FastAPI endpoint: `POST /api/practice` — returns PracticeProblems
  - TDD: Test practice output contains warning disclaimer
  - TDD: Test practice output contains LaTeX equations
  - TDD: Test practice identifies equations/theorems used per step

  **Must NOT do**:
  - NEVER return practice solutions without the warning disclaimer
  - Do not claim solutions are verified or guaranteed correct

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Prompt engineering for multi-step worked solutions with theorem identification
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 19, 21, 22, 23, 24)
  - **Blocks**: None
  - **Blocked By**: Task 19

  **Acceptance Criteria**:
  - [ ] `backend/tests/test_practice_generator.py` → PASS
  - [ ] Warning disclaimer present in EVERY practice response
  - [ ] Each step identifies the equation/theorem being used

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Practice problems include warning and step-by-step solutions
    Tool: Bash (curl)
    Steps:
      1. POST /api/practice with {"topic": "Z-transform", "difficulty": "medium", "count": 2}
      2. Verify response JSON contains 'warning_disclaimer' field
      3. Verify each problem has 'steps' array
      4. Verify at least one step references a named theorem/equation
      5. Verify LaTeX is present in solution steps
    Expected Result: 2 practice problems with LaTeX, step identification, and warning
    Evidence: .sisyphus/evidence/task-20-practice-problems.json

  Scenario: Practice without disclaimer is rejected
    Tool: Bash (pytest)
    Steps:
      1. Mock DeepSeek to return practice problems WITHOUT disclaimer
      2. Verify generator raises error or appends disclaimer automatically
    Expected Result: Disclaimer is always present, even if AI omits it
    Evidence: .sisyphus/evidence/task-20-disclaimer-enforcement.txt
  ```

  **Commit**: YES
  - Message: `feat(practice): AI practice question generator with mandatory warning`
  - Files: `backend/app/services/practice_generator.py`, `backend/app/routers/practice.py`
  - Pre-commit: `cd backend && pytest tests/test_practice_generator.py`

---

- [ ] 21. Conversational Follow-Up Handler

  **What to do**:
  - Create `backend/app/services/conversation.py`:
    - Manages conversation history per session (stored in SQLite, Task 7)
    - `async def handle_followup(conversation_id: str, message: str) -> AsyncGenerator[str, None]`
    - Maintains context: previous query, selected chapters, last explanation
    - Handles follow-up types:
      - "Give me more examples" → generate additional practice problems from same content
      - "Explain step 3 differently" → re-explain specific section with different approach
      - "What about the inverse Z-transform?" → new search with context from previous conversation
      - "Show me the original textbook page" → return raw content reference
    - Sends conversation history to DeepSeek so it has context of what was already discussed
    - Streams responses (reuses Task 19 streaming infrastructure)
  - Update `POST /api/explain` to accept optional `conversation_id`
  - Create `GET /api/conversations/{id}/messages` — retrieve conversation history
  - TDD: Test follow-up maintains conversation context
  - TDD: Test new topic in follow-up triggers fresh search

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Session management + context-aware routing
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 19, 20, 22, 23, 24)
  - **Blocks**: None
  - **Blocked By**: Task 19

  **Acceptance Criteria**:
  - [ ] `backend/tests/test_conversation.py` → PASS
  - [ ] Follow-ups reference previous context

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Follow-up question maintains context
    Tool: Bash (curl)
    Steps:
      1. POST /api/search/query with 'Z-transform' → get results
      2. POST /api/explain with selected chapters → get explanation (starts conversation)
      3. POST /api/explain with same conversation_id + 'give me an example problem'
      4. Verify response references Z-transform (context maintained)
    Expected Result: Follow-up answer is about Z-transform without re-specifying
    Evidence: .sisyphus/evidence/task-21-conversation-followup.json
  ```

  **Commit**: YES
  - Message: `feat(chat): conversational follow-up handler with context`
  - Files: `backend/app/services/conversation.py`
  - Pre-commit: `cd backend && pytest tests/test_conversation.py`

---

- [ ] 22. Search Results UI — Categorized List with EXPLAINS/USES Badges

  **What to do**:
  - Create `frontend/src/components/SearchResults.tsx`:
    - Renders categorized search results in the left chat panel (DeskPage)
    - Each result shows:
      - PixelBadge: green "EXPLAINS" or blue "USES" (from Task 11)
      - Chapter title + textbook name
      - Confidence indicator (pixel-styled progress bar or stars)
      - Brief reason for classification
      - Checkbox for selection
    - "EXPLAINS" results grouped first, then "USES" (backend sort order)
    - "Select All EXPLAINS" quick button
    - "Generate Explanation" button (sends selected to /api/explain)
    - "Generate Practice Problems" button
  - Create `frontend/src/api/search.ts` — API client:
    - `searchQuery(query: string): Promise<CategorizedResults>`
    - `generateExplanation(chapterIds: string[], query: string): Promise<ReadableStream>`
  - Integrate into DeskPage: user types query → results appear → user selects → explanation streams into book panel
  - TDD: Test SearchResults renders EXPLAINS badge with green color
  - TDD: Test selection checkboxes work

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Visual design of search results with badges and interactive selection
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 19, 20, 21, 23, 24)
  - **Blocks**: None
  - **Blocked By**: Tasks 15, 17

  **Acceptance Criteria**:
  - [ ] `frontend/src/__tests__/SearchResults.test.tsx` → PASS
  - [ ] EXPLAINS and USES badges visually distinct

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Search results display with correct badges
    Tool: Playwright
    Steps:
      1. Navigate to desk view
      2. Type 'Z-transform' in chat input, press Enter
      3. Wait for results to appear
      4. Verify green 'EXPLAINS' badge exists
      5. Verify blue 'USES' badge exists (if applicable)
      6. Click checkbox on first result
      7. Click 'Generate Explanation' button
    Expected Result: Categorized results with colored badges, selection works
    Evidence: .sisyphus/evidence/task-22-search-results.png
  ```

  **Commit**: YES
  - Message: `feat(ui): search results with EXPLAINS/USES badges and selection`
  - Files: `frontend/src/components/SearchResults.tsx`, `frontend/src/api/search.ts`
  - Pre-commit: `cd frontend && npx vitest run`

---

- [ ] 23. Explanation View — Streaming Book Panel with LaTeX + Images

  **What to do**:
  - Create `frontend/src/components/ExplanationView.tsx`:
    - Renders inside the right "book" panel of DeskPage
    - Connects to SSE streaming endpoint (/api/explain) via EventSource or fetch
    - As chunks arrive: progressively renders Markdown+LaTeX using ContentRenderer (Task 18)
    - "Writing" animation: cursor blink or ink-drop effect as new content appears
    - Source citations rendered as clickable links: click → jumps to raw textbook viewer (Task 24)
    - Images from source chapters displayed inline
    - At the end of explanation: "Generate Practice Problems" button
    - Warning disclaimers render as prominent alert boxes
  - Handle streaming lifecycle: loading state → streaming → complete → follow-up input
  - TDD: Test streaming chunks progressively update rendered content
  - TDD: Test source citations render as clickable links

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Streaming UX + visual "book writing" effect
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 19, 20, 21, 22, 24)
  - **Blocks**: None
  - **Blocked By**: Tasks 18, 19

  **Acceptance Criteria**:
  - [ ] `frontend/src/__tests__/ExplanationView.test.tsx` → PASS
  - [ ] Streaming content renders progressively (not all at once)
  - [ ] LaTeX equations render correctly during streaming

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Streaming explanation renders progressively with LaTeX
    Tool: Playwright
    Steps:
      1. Trigger explanation generation from search results
      2. Observe right panel: content should appear incrementally
      3. Wait for completion
      4. Verify .katex elements exist (equations rendered)
      5. Verify '[Source:' text visible (citations present)
      6. Screenshot final state
    Expected Result: Progressive rendering with equations and citations
    Evidence: .sisyphus/evidence/task-23-streaming-explanation.png
  ```

  **Commit**: YES
  - Message: `feat(ui): streaming explanation book panel with LaTeX + citations`
  - Files: `frontend/src/components/ExplanationView.tsx`
  - Pre-commit: `cd frontend && npx vitest run`

---

- [ ] 24. Raw Textbook Viewer — PDF Page Display with Images

  **What to do**:
  - Create `frontend/src/components/TextbookViewer.tsx`:
    - Shows original textbook content for a specific chapter/page range
    - Displays: extracted text + extracted images from that chapter
    - Chapter text rendered with ContentRenderer (Task 18) for any embedded LaTeX
    - Images displayed in reading order (based on page + image index from Task 8)
    - Page navigation: prev/next buttons to move between pages in the chapter
    - "Open in full screen" option for detailed reading
    - Triggered when user clicks source citation in explanation view
  - Create FastAPI endpoint: `GET /api/textbooks/{id}/chapters/{chapter_num}/content` — returns chapter text + image references
  - Create `frontend/src/api/chapters.ts` API client
  - TDD: Test TextbookViewer renders chapter text and images
  - TDD: Test page navigation works within chapter

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Reading experience design
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 19, 20, 21, 22, 23)
  - **Blocks**: None
  - **Blocked By**: Tasks 8, 17

  **Acceptance Criteria**:
  - [ ] `frontend/src/__tests__/TextbookViewer.test.tsx` → PASS
  - [ ] Chapter text + images render correctly

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Raw textbook chapter displays text and images
    Tool: Playwright
    Steps:
      1. Navigate to textbook viewer for a chapter from test textbook
      2. Verify chapter text is visible
      3. Verify at least 1 image displays (from extracted images)
      4. Click next page button, verify content updates
    Expected Result: Readable chapter content with images and navigation
    Evidence: .sisyphus/evidence/task-24-textbook-viewer.png
  ```

  **Commit**: YES
  - Message: `feat(ui): raw textbook viewer with images and page navigation`
  - Files: `frontend/src/components/TextbookViewer.tsx`, `frontend/src/api/chapters.ts`
  - Pre-commit: `cd frontend && npx vitest run`

---

- [ ] 25. Material Organizer — Auto-Categorize Downloaded Files into Folders

  **What to do**:
  - Create `backend/app/services/material_organizer.py`:
    - `async def organize_materials(source_dir: str, dest_dir: str) -> OrganizationResult`
    - Scans source directory for all PDF/PPTX/DOCX files
    - For each file: extracts first few pages of text using document_parser (Task 9 dispatcher)
    - Sends extracted text to DeepSeek (deepseek-chat) with prompt:
      - "Classify this academic document into ONE category: lecture_slides, tutorial_questions, tutorial_solutions, past_exam_papers, lab_manual, reference_notes, other. Also extract: course code, document title, date if visible. Return JSON."
    - Moves/copies files into categorized subdirectories: `{dest_dir}/lectures/`, `{dest_dir}/tutorials/`, etc.
    - Generates a .md description for each document (slide-by-slide or page-by-page summary)
    - Description format: 'Slide 2-3: Derivation of Z-transform. Slide 5-10: Example of pole-zero placement.'
  - Create FastAPI endpoint: `POST /api/organize` — accepts source_dir + dest_dir
  - Create FastAPI endpoint: `GET /api/organize/{job_id}/status` — progress tracking
  - TDD: Test classification of a lecture PDF vs exam paper
  - TDD: Test file is moved to correct subdirectory
  - TDD: Test .md description is generated for each file

  **Must NOT do**:
  - Do not modify original files — copy, don't move (keep originals intact)
  - Do not process files already organized (check for duplicate detection)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: AI classification + file operations + description generation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Tasks 26, 27, 28, 29)
  - **Blocks**: None
  - **Blocked By**: Tasks 8, 9, 10

  **References**:

  **Pattern References**:
  - Task 9 `document_parser.py` — Unified parser dispatcher for file type detection
  - Task 10 `description_generator.py` — Re-use description generation pattern but adapted for lecture materials
  - `Simulation Material/University Material/` — Real lecture PDFs for testing

  **Acceptance Criteria**:
  - [ ] `backend/tests/test_material_organizer.py` → PASS
  - [ ] Files organized into correct subdirectories
  - [ ] .md description generated per document with slide/page breakdown

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Lecture PDFs auto-categorized into correct folders
    Tool: Bash (curl + file checks)
    Preconditions: Simulation Material/University Material/ contains lecture PDFs
    Steps:
      1. POST /api/organize with source_dir='Simulation Material/University Material/', dest_dir=test_output/
      2. Wait for completion
      3. Check: ls test_output/lectures/ — verify lecture PDFs moved here
      4. Check: ls test_output/ for .md description files
    Expected Result: PDFs categorized as 'lecture_slides', .md descriptions generated
    Failure Indicators: Files in wrong category, no descriptions, 500 errors
    Evidence: .sisyphus/evidence/task-25-organize.txt
  ```

  **Commit**: YES
  - Message: `feat(organizer): auto-categorize course materials into folders with descriptions`
  - Files: `backend/app/services/material_organizer.py`, `backend/app/routers/organize.py`
  - Pre-commit: `cd backend && pytest tests/test_material_organizer.py`

---

- [ ] 26. Textbook Finder — AI Recommends Textbooks + Links

  **What to do**:
  - Create `backend/app/services/textbook_finder.py`:
    - `async def find_textbooks(course_descriptions: list[str]) -> list[TextbookRecommendation]`
    - Takes descriptions of course materials (from Task 10/25 descriptions)
    - Sends to DeepSeek with prompt:
      - "Based on these course materials about [inferred topic], recommend 3-5 textbooks. For each: title, author, ISBN, why it's relevant, and where to find it legally (OpenStax, university library, publisher website). Also infer the overall course topic from the equations and concepts mentioned."
    - Returns structured recommendations with links to legal sources
    - Searches OpenStax API for free alternatives
    - Searches Google Books API for metadata + preview links
    - NEVER provides links to pirated content
  - Create FastAPI endpoint: `POST /api/textbooks/recommend` — returns TextbookRecommendation list
  - TDD: Test recommendation includes title, author, legal source link
  - TDD: Test course topic inference from Control & Robotics materials

  **Must NOT do**:
  - NEVER link to Library Genesis, Z-Library, or any piracy sites
  - NEVER download textbooks automatically — only recommend with links

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: API integration + AI prompting
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Tasks 25, 27, 28, 29)
  - **Blocks**: None
  - **Blocked By**: Tasks 5, 10

  **References**:

  **External References**:
  - OpenStax API: `https://openstax.org/` — Free textbooks for common courses
  - Google Books API: `https://developers.google.com/books/docs/v1/using` — Search + preview links

  **Acceptance Criteria**:
  - [ ] `backend/tests/test_textbook_finder.py` → PASS
  - [ ] Recommendations include legal source links only
  - [ ] Course topic correctly inferred from materials

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Textbook recommendations for Control & Robotics course
    Tool: Bash (curl)
    Steps:
      1. POST /api/textbooks/recommend with descriptions from test textbook
      2. Verify response contains 3+ recommendations
      3. Verify each has: title, author, legal_source_url
      4. Verify NO urls contain 'libgen', 'z-lib', or known piracy domains
    Expected Result: Relevant textbook recommendations with legal links
    Evidence: .sisyphus/evidence/task-26-recommendations.json
  ```

  **Commit**: YES
  - Message: `feat(finder): AI textbook recommender with legal source links`
  - Files: `backend/app/services/textbook_finder.py`, `backend/app/routers/textbooks.py` (updated)
  - Pre-commit: `cd backend && pytest tests/test_textbook_finder.py`

---

- [ ] 27. LMS Downloader — Playwright Embedded Browser for Moodle

  **What to do**:
  - Create `backend/app/services/lms_downloader.py`:
    - Uses Playwright (async) to automate course material downloads
    - `async def start_lms_session(lms_url: str) -> BrowserSession`
    - Flow:
      1. Opens embedded Chromium browser window (visible to user)
      2. Navigates to LMS login page (e.g., UCL Moodle)
      3. **User logs in manually** — app waits, does NOT handle credentials
      4. After login detected (URL change or cookie check): app takes control
      5. Navigates to course page, lists available materials
      6. Presents file list to user via API → user selects which to download
      7. Downloads selected files to specified directory
    - Moodle-specific logic (expandable to other LMS later):
      - Detect course sections, resource links, file types
      - Handle Moodle's redirect-based file downloads
    - Save browser session state (cookies) for future use (avoid re-login)
  - Create FastAPI WebSocket endpoint: `WS /api/lms/session` — real-time communication with browser automation
  - Create FastAPI endpoints:
    - `POST /api/lms/start` — launches browser
    - `GET /api/lms/courses` — lists detected courses after login
    - `GET /api/lms/courses/{id}/materials` — lists downloadable materials
    - `POST /api/lms/download` — downloads selected materials
  - TDD: Test session state saves and restores cookies
  - TDD: Test file list parsing from Moodle HTML structure

  **Must NOT do**:
  - NEVER store user credentials (username/password) — session cookies ARE allowed to persist (opt-in) as they are session tokens, not credentials
  - NEVER auto-fill login forms
  - NEVER bypass authentication mechanisms
  - Do not support other LMS platforms yet — Moodle first, architecture must be extensible

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Browser automation with real-world website interaction, complex async flows
  - **Skills**: [`playwright`]
    - `playwright`: Required for browser automation patterns

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Tasks 25, 26, 28, 29)
  - **Blocks**: None
  - **Blocked By**: Tasks 2, 4

  **References**:

  **External References**:
  - Playwright Python: `https://playwright.dev/python/docs/intro` — Async API, persistent contexts
  - Moodle-DL: `https://github.com/C0D3D3V/Moodle-DL` — Reference for Moodle file discovery patterns
  - Moodle web service API: `https://docs.moodle.org/dev/Web_service_API_functions` — Alternative to scraping

  **Acceptance Criteria**:
  - [ ] `backend/tests/test_lms_downloader.py` → PASS
  - [ ] Browser launches and user can log in manually
  - [ ] Session cookies persist for reuse (opt-in, stored locally — these are session tokens, not credentials)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Browser launches and waits for manual login
    Tool: Playwright (via pytest)
    Steps:
      1. Call start_lms_session('https://moodle.ucl.ac.uk')
      2. Verify Chromium window opens
      3. Verify app waits without filling any form fields
      4. Verify no username/password stored in any config/DB/file (session cookies ARE expected to persist)
    Expected Result: Browser opens to Moodle login, no auto-fill
    Failure Indicators: Credentials found in storage, form auto-filled, browser doesn't open
    Evidence: .sisyphus/evidence/task-27-browser-launch.png
  ```

  **Commit**: YES
  - Message: `feat(lms): Playwright-based Moodle downloader with manual login`
  - Files: `backend/app/services/lms_downloader.py`, `backend/app/routers/lms.py`
  - Pre-commit: `cd backend && pytest tests/test_lms_downloader.py`

---

- [ ] 28. Loading/Splash Screen — Pixel Art Startup Animation

  **What to do**:
  - Create `frontend/src/components/SplashScreen.tsx`:
    - Displays while Python backend is starting (2-5 seconds)
    - Pixel art animation: book opening, pages flipping, or quill writing
    - "Lazy Learn" title in Press Start 2P font with typing animation
    - Subtitle: 'Loading study assistant...' with pixel loading bar
    - Polls backend `GET /health` endpoint every 500ms
    - Automatically transitions to Bookshelf when backend responds
  - CSS-only animation (no sprite sheets needed for MVP)
  - TDD: Test SplashScreen renders title
  - TDD: Test transition triggers when health check succeeds

  **Must NOT do**:
  - Do not create complex sprite animations — CSS-only for MVP

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Animation + visual design
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Tasks 25, 26, 27, 29)
  - **Blocks**: None
  - **Blocked By**: Task 11

  **Acceptance Criteria**:
  - [ ] `frontend/src/__tests__/SplashScreen.test.tsx` → PASS
  - [ ] Animation displays during backend startup
  - [ ] Auto-transitions when backend is ready

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Splash screen shows during backend startup
    Tool: Playwright
    Steps:
      1. Open app WITHOUT backend running
      2. Verify splash screen with 'Lazy Learn' title visible
      3. Verify loading animation is playing
      4. Start backend in background
      5. Wait for auto-transition to bookshelf (within 10s)
    Expected Result: Splash screen shows, transitions once backend is up
    Evidence: .sisyphus/evidence/task-28-splash-screen.png
  ```

  **Commit**: YES
  - Message: `feat(ui): pixel art splash screen with backend health polling`
  - Files: `frontend/src/components/SplashScreen.tsx`
  - Pre-commit: `cd frontend && npx vitest run`

---

- [ ] 29. Settings Panel — API Keys, Download Folder, Course Management

  **What to do**:
  - Create `frontend/src/pages/SettingsPage.tsx`:
    - Accessible from bookshelf via gear icon (pixel-styled cog)
    - Sections:
      - **API Keys**: DeepSeek API key input (masked), OpenAI API key input (optional, masked), test connection buttons
      - **Download Folder**: File picker for default download/data directory
      - **Courses**: List of courses, add/remove course, assign textbooks to courses
      - **Math Library**: Manage always-available math reference textbooks
      - **Quick Ref Defaults**: Configure default pinned formulas/tables for Quick Ref sidebar
    - Settings persisted via backend API to SQLite / config file
    - ESC to close settings and return to bookshelf
  - Create FastAPI endpoints:
    - `GET /api/settings` — retrieve current settings
    - `PUT /api/settings` — update settings
    - `POST /api/settings/test-connection` — test AI provider connectivity
  - Create `backend/app/services/settings.py` — settings persistence
  - TDD: Test settings save and load roundtrip
  - TDD: Test API key masking (never return full key in GET response)
  - TDD: Test connection test endpoint validates API key

  **Must NOT do**:
  - NEVER return full API keys in API responses — mask all but last 4 characters
  - Do not store API keys in plaintext files — use OS keychain or encrypted storage if feasible, or at minimum SQLite with warning

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Settings form design with pixel art styling
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Tasks 25, 26, 27, 28)
  - **Blocks**: None
  - **Blocked By**: Tasks 11, 17

  **References**:

  **Pattern References**:
  - Task 11 pixel components — PixelInput (masked variant for API keys), PixelButton, PixelPanel
  - Task 7 storage service — SQLite for settings persistence

  **Acceptance Criteria**:
  - [ ] `frontend/src/__tests__/SettingsPage.test.tsx` → PASS
  - [ ] `backend/tests/test_settings.py` → PASS
  - [ ] API keys are masked in responses
  - [ ] Settings persist across app restarts

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Settings save and load with masked API keys
    Tool: Playwright + Bash (curl)
    Steps:
      1. Navigate to settings page
      2. Enter DeepSeek API key in masked input field
      3. Click Save
      4. Reload page
      5. Verify API key field shows '****...d4c7' (masked)
      6. curl GET /api/settings — verify api_key field is masked
      7. Click 'Test Connection' — verify success response
    Expected Result: Key saved, displayed masked, connection works
    Failure Indicators: Full key visible in UI or API response, connection test fails
    Evidence: .sisyphus/evidence/task-29-settings.png
  ```

  **Commit**: YES
  - Message: `feat(settings): API keys, courses, download folder, quick ref config`
  - Files: `frontend/src/pages/SettingsPage.tsx`, `backend/app/services/settings.py`, `backend/app/routers/settings.py`
  - Pre-commit: `cd backend && pytest tests/test_settings.py && cd ../frontend && npx vitest run`

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns (ChromaDB imports, vector DB references, credential storage) — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan. Verify "verify solutions" warning appears on all practice problem outputs.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest` + `vitest` + `pyright`/`mypy` type checks. Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names. Verify all API calls have retry logic. Verify streaming is implemented for explanation endpoints.
  Output: `Build [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA — Full Flow with Simulation Materials** — `unspecified-high` (+ `playwright` skill)
  Start app. Import `Simulation Material/Textbook/DigitalControlSystems-NeweditionI.D.LandauG.Zito.pdf`. Wait for processing. Search "Z-transform". Verify EXPLAINS vs USES categorization appears. Select a chapter. Verify streaming explanation with LaTeX renders correctly. Request practice problems. Verify "verify solutions" warning appears. Test conversational follow-up. Screenshot each step. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built, nothing beyond spec was built. Specifically check: no ChromaDB/embeddings snuck in, no credential storage, no direct textbook downloads, no cloud features. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **T1**: `spike(core): validate PDF extraction and DeepSeek API feasibility`
- **T2-T7**: `feat(scaffold): project foundation — backend, frontend, tauri, AI layer, schema, storage`
- **T8-T9**: `feat(parser): PDF/PPT/DOCX text + image + TOC extraction pipeline`
- **T10**: `feat(descriptions): AI-generated chapter/subchapter .md descriptions`
- **T11**: `feat(ui): pixel art design system — theme, fonts, base components`
- **T12**: `feat(ai): OpenAI vision provider (optional)`
- **T13-T15**: `feat(search): hybrid search pipeline — concept extraction, keyword, AI categorization`
- **T16-T18**: `feat(ui): bookshelf, desk, and content renderer views`
- **T19-T21**: `feat(explain): AI explanation engine with streaming, practice problems, conversation`
- **T22-T24**: `feat(ui): search results, explanation book panel, raw PDF viewer`
- **T25-T29**: `feat(modules): organizer, textbook finder, LMS downloader, settings`

---

## Success Criteria

### Verification Commands
```bash
cd backend && pytest                    # Expected: all tests pass
cd frontend && npx vitest run           # Expected: all tests pass
cd src-tauri && cargo build             # Expected: successful build
# Full flow: import textbook → search → explain → practice problems
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass
- [ ] Simulation Material/ textbook works end-to-end
- [ ] LaTeX equations render correctly in UI
- [ ] Images from PDFs display in UI
- [ ] "Verify solutions" warning on all practice problems
- [ ] Streaming responses work for explanations
- [ ] Pixel art theme applied consistently
