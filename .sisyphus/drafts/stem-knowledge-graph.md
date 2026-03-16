# Draft: STEM Knowledge Graph Feature

## Requirements (confirmed)
- Build a GitNexus-like knowledge graph for STEM subjects
- Integrate into existing Lazy Learn framework
- Entry point: "Generate Relationship" button in CoursePreviewView
- Graph shows relationships: theorems, proofs, derivations, logical reasoning chains
- Content sourced primarily from MinerU-extracted content
- Interactive graph visualization for students

## User's Vision
- STEM subjects have inherent logical relationships (math proofs, logical reasoning)
- These can be presented as a graph — similar to how GitNexus maps code relationships
- Students see the full graph of relationships between ideas

## Research Findings

### Architecture (confirmed)
- **Frontend**: React 19 + TypeScript + Vite (custom pixel-art UI system, NO external lib)
- **Backend**: FastAPI + Python 3.11+ (async throughout)
- **Database**: SQLite with aiosqlite (raw SQL, no ORM)
- **Desktop**: Tauri wrapper
- **AI**: DeepSeek (primary) + OpenAI (fallback) via AIRouter
- **State**: Custom hooks (useConversation, usePanelLayout, usePinnedItems), no Redux
- **API pattern**: fetch-based clients in `src/api/`, Pydantic models on backend

### CoursePreviewView (integration point)
- Located: `frontend/src/components/CoursePreviewView.tsx`
- Has access to: Course, Textbook[], UniversityMaterial[], PipelineStatus, ChapterWithStatus[]
- Uses PixelButton (primary/secondary/danger), PixelDialog for modals
- Three-panel layout: Textbooks | Materials | Chapter/Topic Browser
- Best integration: Add "Generate Relationship" button in `.preview-header`
- Display graph via PixelDialog modal (already in codebase)

### MinerU Pipeline
- Extracts: text, equations (LaTeX), images, tables from PDFs
- Output format: `document_content_list.json` with typed entries (text, equation, image, table)
- Storage: `extracted_content` DB table + disk `.md` files in `data/textbooks/{id}/chapters/{n}/content/`
- Pipeline phases: upload → TOC extraction → verification → content extraction → description generation
- Hook point for graph: AFTER `ContentExtractor._store_chapter_entries()` completes

### Database Schema (existing)
- Tables: courses, textbooks, chapters, sections (self-referential hierarchy), extracted_content, material_summaries, material_relevance_results, conversations, messages, university_materials, settings
- Migration pattern: idempotent in-code migrations (V2 pattern with try/except)
- No existing graph/relationship tables for concept linking
- `description_schema.py` has `prerequisites` field in ChapterDescription (unused for graph)

### Graph Visualization Options
- **React Flow** (@xyflow/react) — RECOMMENDED: native React, custom nodes/edges, 100-500 nodes, built-in zoom/pan/minimap
- **Cytoscape.js** — Alternative if graph algorithms needed (shortest path, centrality)
- **Sigma.js** — Overkill (WebGL, designed for 100K+ nodes)
- No existing graph/visualization libraries in the codebase

### LLM-Based Extraction
- Use structured prompts to extract triples: (subject, predicate, object)
- Relationship types: derives_from, uses, proves, generalizes, specializes, prerequisite_of
- Can leverage existing AIRouter (DeepSeek/OpenAI) — no new provider needed

## Technical Decisions (confirmed)
- **Visualization**: React Flow (@xyflow/react) — native React, custom nodes
- **Scope**: Per-textbook first (MVP). Cross-textbook later.
- **Trigger**: On-demand — user clicks "Generate Relationship" button
- **Storage**: Extend SQLite with new tables (concept_nodes + concept_edges)
- **LLM**: Use existing AIRouter (DeepSeek/OpenAI) — no new provider
- **Granularity**: Multi-level expandable (chapter → section → equation drill-down)
- **Tests**: TDD (pytest-asyncio backend, vitest frontend)

## Decisions (Round 2 — confirmed)
- **Relationship types**: derives_from, proves, prerequisite_of, uses/applies, generalizes/specializes, contradicts/contrasts, defines, equivalent_form (e.g., equivalent circuits — same topic, different representation)
- **Graph display**: Dedicated new page `/graph/:textbookId` with its own route
- **Node click behavior**: Show concept details panel (definition, source chapter/page, related equations)

## Open Questions (remaining)
- None — all critical decisions made

## Scope Boundaries
- INCLUDE: (to be defined after discussion)
- EXCLUDE: (to be defined after discussion)
