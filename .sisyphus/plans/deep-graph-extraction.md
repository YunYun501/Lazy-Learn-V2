# Deep Knowledge Graph Extraction — A+B Hybrid (Multi-Level)

> **IMPORTANT**: This plan extends the STEM Knowledge Graph feature that already exists in the
> `feature/stem-knowledge-graph` branch (worktree: `C:\Local\Github\Lazy_Learn_stem`).
> All referenced files (knowledge_graph_builder.py, latex_parser.py, EquationNode.tsx, etc.)
> either already exist in that worktree or will be created by this plan's tasks.
> The main repo (`C:\Local\Github\Lazy_Learn`) does NOT contain these files — they are on the feature branch.

## TL;DR

> **Quick Summary**: Extend the STEM knowledge graph from 2 levels (chapter/section) to 4 levels (chapter/section/concept/equation) using Approach A (LLM per-section concept extraction) and Approach B (deterministic LaTeX equation parsing with variable co-occurrence).
> 
> **Deliverables**:
> - Backend: LaTeX equation parser, section-content mapper, enhanced graph builder with per-section extraction + equation-level nodes
> - Frontend: Multi-level graph with equation nodes (KaTeX rendered), variable-shared edges, deeper expand/collapse
> - New edge types: shared_variables (deterministic), equation-level derives_from
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES — 4 waves
> **Critical Path**: LaTeX parser + section mapper → enhanced builder → frontend updates → integration tests

---

## Context

### Original Request
Current knowledge graph only shows section-level topics (21 nodes, 20 edges for a textbook with 2 extracted chapters). User wants deeper granularity — down to individual equations with mathematical relationships detected deterministically (like GitNexus uses AST parsing for code), not LLM-guessed.

### Approach
- **Approach A** (LLM): Extract concepts PER SECTION (not per chapter). Full section text + equations fed to LLM. Currently truncates to 3000 chars per chapter — will now process each section individually with full content.
- **Approach B** (Deterministic): Parse LaTeX equations to extract variables. Build variable co-occurrence graph (equations sharing variables are likely related). Use LLM only to classify the relationship type (derivation, substitution, approximation).
- **Section paths**: Map content to sections via page_number matching against section page_start/page_end. Compute paths like CH7/7.1/7.1.2 during graph build.

### Metis Review
- Section-to-content mapping via page_number (no schema migration needed)
- Regex-based LaTeX parser with 3-layer pipeline (clean, extract, filter)
- Concept deduplication across sections (same title = same node)
- Skip strategy for unparseable equations

---

## Work Objectives

### Core Objective
Produce a 4-level knowledge graph where conceptual relationships are LLM-extracted and mathematical relationships are deterministically parsed.

### Concrete Deliverables
- `backend/app/services/latex_parser.py` — deterministic LaTeX variable extractor
- `backend/app/services/section_content_mapper.py` — maps extracted_content to sections via page ranges
- Enhanced `backend/app/services/knowledge_graph_builder.py` — per-section extraction + equation nodes + variable edges
- Enhanced `backend/app/services/knowledge_graph_prompts.py` — per-section concept prompt
- Updated `frontend/src/components/graph/EquationNode.tsx` — render LaTeX in graph nodes
- Updated expand/collapse to handle 4 levels

### Definition of Done
- [ ] Graph for Chapter 7 (Shafts, 434 content entries) produces 50+ nodes across 4 levels
- [ ] Equation nodes display LaTeX via KaTeX
- [ ] shared_variables edges connect equations sharing symbols
- [ ] Per-section LLM extraction produces sub-topic concepts
- [ ] All tests pass (backend + frontend)

### Must Have
- 4-level hierarchy: chapter → section → concept → equation
- Section-content mapping via page_number ranges
- LaTeX variable extraction (regex, 3-layer pipeline)
- Variable co-occurrence edges (deterministic, no LLM)
- Per-section concept extraction (LLM, full section content)
- Concept deduplication across sections
- Equation nodes with KaTeX rendering

### Must NOT Have (Guardrails)
- No NetworkX dependency (plain Python dicts for co-occurrence)
- No SymPy dependency (regex-based parsing only)
- No extracted_content schema migration (compute section mapping at build time)
- No individual variable nodes (Level 5 deferred)
- No figure nodes
- No LaTeX custom macro resolution (skip unparseable)
- No cross-textbook relationships

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: YES (pytest-asyncio backend, vitest frontend)
- **Automated tests**: TDD
- **Framework**: pytest (backend), vitest (frontend)

### QA Policy
Every task MUST include agent-executed QA scenarios.

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — new services + models):
├── Task 1: LaTeX equation parser service [deep]
├── Task 2: Section-content mapper service [unspecified-high]
├── Task 3: New Pydantic models + NodeLevel/edge types [quick]
└── Task 4: Per-section concept extraction prompt [quick]

Wave 2 (Core — enhanced builder):
├── Task 5: Enhanced KnowledgeGraphBuilder — per-section extraction (depends: 2, 3, 4) [deep]
├── Task 6: Equation node creation + variable co-occurrence edges (depends: 1, 2, 3) [deep]
└── Task 7: Concept deduplication logic (depends: 3, 5) [unspecified-high]

Wave 3 (Frontend — deeper graph visualization):
├── Task 8: EquationNode with KaTeX rendering update (depends: 3) [visual-engineering]
├── Task 9: 4-level expand/collapse (depends: 5, 6) [deep]
├── Task 10: Edge styling for shared_variables type (depends: 6) [visual-engineering]
└── Task 11: Section path display in ConceptDetailPanel (depends: 2) [quick]

Wave 4 (Integration + Verification):
├── Task 12: Integration test — full 4-level pipeline (depends: all) [deep]
└── Task 13: Manual QA — regenerate graph on Mechanical Design textbook [unspecified-high]

Critical Path: Task 1 → Task 6 → Task 9 → Task 12
              Task 2 → Task 5 → Task 7 → Task 12
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 4 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | 6 | 1 |
| 2 | — | 5, 6, 11 | 1 |
| 3 | — | 5, 6, 7, 8 | 1 |
| 4 | — | 5 | 1 |
| 5 | 2, 3, 4 | 7, 9 | 2 |
| 6 | 1, 2, 3 | 9, 10 | 2 |
| 7 | 3, 5 | 12 | 2 |
| 8 | 3 | 12 | 3 |
| 9 | 5, 6 | 12 | 3 |
| 10 | 6 | 12 | 3 |
| 11 | 2 | 12 | 3 |
| 12 | all | 13 | 4 |
| 13 | 12 | — | 4 |

---

## TODOs

- [x] 1. LaTeX Equation Parser Service

  **What to do**:
  - Create `backend/app/services/latex_parser.py`
  - Implement 3-layer pipeline: clean MinerU artifacts, extract variables by pattern, filter exclusions
  - Layer 1 `clean_mineru_artifacts(latex: str) -> str`: strip `$$` delimiters, normalize whitespace, remove `\llap`/`\marginpar`, fix broken backslashes
  - Layer 2 `extract_variables(latex: str) -> set[str]`: separate regex patterns for: basic single-letter vars (`[a-zA-Z]`), Greek letters (`\alpha`, `\omega`, `\theta`...), subscripted vars (`x_{1}`, `\omega_{c}`), superscripted vars (`x^{2}` — extract `x` not the exponent), vectors/bold (`\vec{v}`, `\mathbf{F}`), partial derivatives (`\frac{\partial f}{\partial x}` — extract `f` and `x`)
  - Layer 3 `filter_variables(vars: set[str]) -> set[str]`: remove constants (`CONSTANTS = frozenset({'e', 'i', 'pi', 'infty'})`), operators (`OPERATORS = frozenset({'sin', 'cos', 'tan', 'log', 'ln', 'exp', 'lim', 'max', 'min', 'det', 'sup', 'inf'})`), LaTeX commands (`\frac`, `\int`, `\sum`)
  - Top-level function `parse_equation(latex: str) -> EquationInfo` where `EquationInfo` has: `raw_latex`, `variables: set[str]`, `is_parseable: bool`
  - Function `build_variable_cooccurrence(equations: list[EquationInfo]) -> list[tuple[str, str, int]]` — returns pairs of equation IDs that share variables, with count of shared vars as weight. Use plain `defaultdict(int)`, NOT NetworkX.
  - TDD: write tests FIRST

  **Must NOT do**:
  - No SymPy dependency
  - No NetworkX dependency
  - No custom macro resolution (skip equations with `\newcommand`)
  - Constants/operators must be module-level `frozenset` constants, not inline

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4)
  - **Blocks**: Task 6
  - **Blocked By**: None

  **References**:
  - `backend/app/services/knowledge_graph_prompts.py` — existing prompt/parser pattern
  - Sample equations from DB: `$$\omega_{c} = \sqrt{g/y}$$`, `$$\frac{1}{\omega_c^2} = \frac{1}{\omega_1^2} + \frac{1}{\omega_2^2}$$`

  **Acceptance Criteria**:
  - [ ] `parse_equation('$$\\omega_{c} = \\sqrt{g/y}$$')` returns variables `{'omega_c', 'g', 'y'}`
  - [ ] `parse_equation('$$\\sin(\\theta)$$')` returns `{'theta'}` (sin filtered as operator)
  - [ ] `parse_equation('$$\\frac{\\partial f}{\\partial x}$$')` returns `{'f', 'x'}`
  - [ ] `build_variable_cooccurrence` returns pairs sharing variables
  - [ ] Unparseable equations return `is_parseable=False`, empty variables, no crash
  - [ ] `cd backend && python -m pytest tests/test_latex_parser.py -v` passes (8+ tests)

  **QA Scenarios**:
  ```
  Scenario: Parse real MinerU equations from Chapter 7
    Tool: Bash (python)
    Steps:
      1. Load 10 equations from extracted_content where chapter_id = '8fdccd34...'
      2. Run parse_equation on each
      3. Assert at least 7/10 return is_parseable=True with non-empty variables
    Evidence: .sisyphus/evidence/task-1-latex-parser.txt

  Scenario: Variable co-occurrence detects shared symbols
    Tool: Bash (python)
    Steps:
      1. Parse 5 equations containing omega_c
      2. Run build_variable_cooccurrence
      3. Assert pairs exist with shared_count > 0
    Evidence: .sisyphus/evidence/task-1-cooccurrence.txt
  ```

  **Commit**: YES (groups with Tasks 2, 3, 4)

- [x] 2. Section-Content Mapper Service

  **What to do**:
  - Create `backend/app/services/section_content_mapper.py`
  - Map extracted_content entries to sections using page_number matching
  - `async map_content_to_sections(store, chapter_id: str) -> dict[str, list[dict]]`: queries sections for chapter, queries extracted_content for chapter, matches content to section by `section.page_start <= content.page_number <= section.page_end`, returns `{section_id: [content_entries]}`
  - `compute_section_path(store, section_id: str) -> str`: walks parent_section_id chain to build path like `CH7/7.1/7.1.2`. Root section = `CH{chapter_number}/{section_number}`, child = `CH{chapter_number}/{parent_section_number}/{section_number}`
  - Handle content with no page_number (assign to first section of chapter)
  - Handle content that falls outside all section page ranges (assign to nearest section)
  - TDD: write tests FIRST

  **Must NOT do**:
  - No schema migration to extracted_content (compute at build time)
  - No modification to existing sections or extracted_content tables

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4)
  - **Blocks**: Tasks 5, 6, 11
  - **Blocked By**: None

  **References**:
  - `backend/app/services/storage.py` — sections base schema in CREATE_TABLES_SQL (id, chapter_id, section_number, title, page_start, page_end), PLUS `parent_section_id` and `level` columns added in MIGRATE_V2_SQL (lines 95-100: `ALTER TABLE sections ADD COLUMN parent_section_id TEXT`, `ALTER TABLE sections ADD COLUMN level INTEGER DEFAULT 2`)
  - Sections data: 12,811 root (level 2), 84 children (level 3)
  - extracted_content has page_number column
  - NOTE: parent_section_id and level exist in the DB at runtime (V2 migration runs on initialize), even though they're not in the initial CREATE TABLE statement

  **Acceptance Criteria**:
  - [ ] Content with page_number=15 maps to section with page_start=10, page_end=20
  - [ ] Section path for root section returns "CH7/1" format
  - [ ] Section path for child section returns "CH7/1/2" format
  - [ ] Content with no page_number gets assigned to first section
  - [ ] `cd backend && python -m pytest tests/test_section_content_mapper.py -v` passes (5+ tests)

  **QA Scenarios**:
  ```
  Scenario: Map Chapter 7 content to sections
    Tool: Bash (python)
    Steps:
      1. Call map_content_to_sections for chapter 8fdccd34
      2. Assert sections with content entries > 0
      3. Assert no content entries are orphaned (unmapped)
    Evidence: .sisyphus/evidence/task-2-section-mapper.txt
  ```

  **Commit**: YES (groups with Tasks 1, 3, 4)

- [x] 3. Extended Models + Node/Edge Types

  **What to do**:
  - Update `backend/app/models/knowledge_graph_models.py`: add `NodeLevel.subsection = "subsection"` enum value
  - Add `RelationshipType.shared_variables = "shared_variables"` to the enum
  - Add `RelationshipType.contains = "contains"` (chapter contains section, section contains concept)
  - Add `EquationInfo` Pydantic model: `raw_latex: str`, `variables: list[str]`, `is_parseable: bool`, `source_page: Optional[int]`
  - Update `frontend/src/types/knowledgeGraph.ts`: add `'subsection'` to NodeLevel, `'shared_variables' | 'contains'` to RelationshipType
  - Update `frontend/src/components/graph/edgeStyles.ts`: add styling for `shared_variables` (purple dotted line) and `contains` (thin gray, no arrow)
  - TDD: update model tests + type guard tests

  **Must NOT do**:
  - Do NOT remove existing enum values
  - Do NOT change existing edge styles

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4)
  - **Blocks**: Tasks 5, 6, 7, 8
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] `NodeLevel.subsection` exists
  - [ ] `RelationshipType.shared_variables` exists
  - [ ] Frontend type guards accept new types
  - [ ] Edge styles render for new types
  - [ ] All existing tests still pass
  - [ ] `cd backend && python -m pytest tests/test_knowledge_graph_models.py -v` passes
  - [ ] `cd frontend && npx vitest run src/types/knowledgeGraph.test.ts` passes

  **QA Scenarios**:
  ```
  Scenario: New enum values are valid
    Tool: Bash (python)
    Steps:
      1. cd backend && python -c "from app.models.knowledge_graph_models import NodeLevel, RelationshipType; assert NodeLevel.subsection == 'subsection'; assert RelationshipType.shared_variables == 'shared_variables'; print('ENUMS_OK')"
    Expected Result: Output contains "ENUMS_OK"
    Evidence: .sisyphus/evidence/task-3-enums.txt
  ```

  **Commit**: YES (groups with Tasks 1, 2, 4)

- [x] 4. Per-Section Concept Extraction Prompt

  **What to do**:
  - Add `SECTION_CONCEPT_PROMPT` to `backend/app/services/knowledge_graph_prompts.py`
  - This prompt receives FULL section text + equations (not truncated chapter summary)
  - Template: section_title, section_path, section_text (full), equations_text (all LaTeX from section), parent_concept (the section's parent topic)
  - Ask LLM to extract: sub-concepts, definitions, theorems, lemmas specific to this section
  - Output format: `{{"concepts": [...], "section_relationships": [...]}}` where section_relationships captures intra-section concept links
  - Add `parse_section_concept_response(raw)` parser
  - TDD: write tests FIRST

  **Must NOT do**:
  - Do NOT modify existing CONCEPT_EXTRACTION_PROMPT (keep it for chapter-level)
  - Do NOT truncate section content — pass full text

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3)
  - **Blocks**: Task 5
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] `SECTION_CONCEPT_PROMPT` renders with section_title, section_path, section_text, equations_text, parent_concept
  - [ ] Parser handles dict response with "concepts" key
  - [ ] `cd backend && python -m pytest tests/test_knowledge_graph_prompts.py -v` passes

  **QA Scenarios**:
  ```
  Scenario: Section prompt renders with full content
    Tool: Bash (python)
    Steps:
      1. cd backend && python -c "from app.services.knowledge_graph_prompts import SECTION_CONCEPT_PROMPT; r = SECTION_CONCEPT_PROMPT.format(section_title='Critical Speeds', section_path='CH7/7.3', section_text='Shafts experience resonance...', equations_text='omega_c = sqrt(g/y)', parent_concept='Shafts'); assert 'Critical Speeds' in r; assert 'CH7/7.3' in r; print('PROMPT_OK')"
    Expected Result: Output contains "PROMPT_OK"
    Evidence: .sisyphus/evidence/task-4-prompt.txt
  ```

  **Commit**: YES (groups with Tasks 1, 2, 3)

- [x] 5. Enhanced KnowledgeGraphBuilder — Per-Section Extraction

  **What to do**:
  - Modify `backend/app/services/knowledge_graph_builder.py` build_graph method
  - After creating chapter nodes (Phase 1), add Phase 2: per-section extraction
  - For each chapter: call `map_content_to_sections()` to get content grouped by section
  - For each section with content: create section-level node, then call LLM with `SECTION_CONCEPT_PROMPT` using full section text + equations
  - Create concept nodes at `level='subsection'` linked to section via `contains` edge
  - Deduplicate concepts: if concept title already exists for this textbook, merge (update metadata, don't create duplicate node)
  - Update progress tracking: processed_sections in addition to processed_chapters
  - Keep existing chapter-level extraction (Phase 1) as the fast overview layer

  **Must NOT do**:
  - Do NOT remove existing chapter-level extraction
  - Do NOT truncate section content for LLM calls

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7)
  - **Blocks**: Tasks 7, 9
  - **Blocked By**: Tasks 2, 3, 4

  **Acceptance Criteria**:
  - [ ] Builder creates section-level nodes from sections table
  - [ ] Per-section LLM extraction produces subsection-level concept nodes
  - [ ] Duplicate concepts merged (same title = one node)
  - [ ] Progress tracking shows section progress
  - [ ] `cd backend && python -m pytest tests/test_knowledge_graph_builder.py -v` passes

  **QA Scenarios**:
  ```
  Scenario: Per-section extraction produces deeper nodes
    Tool: Bash (pytest)
    Steps:
      1. Create test with mock AIRouter returning section-level concepts
      2. Verify subsection-level nodes created with source_section_id populated
      3. cd backend && python -m pytest tests/test_knowledge_graph_builder.py::test_per_section_extraction -v
    Expected Result: Test passes, subsection nodes exist in DB
    Evidence: .sisyphus/evidence/task-5-per-section.txt
  ```

  **Commit**: YES (groups with Tasks 6, 7)

- [x] 6. Equation Node Creation + Variable Co-occurrence Edges

  **What to do**:
  - Add Phase 3 to knowledge_graph_builder: equation-level node creation
  - For each section's content: filter `content_type='equation'` entries
  - For each equation: call `parse_equation()` from latex_parser
  - Create concept_node with `level='equation'`, `node_type='equation'`, `metadata_json` containing `{"variables": [...], "raw_latex": "..."}`, `source_page` from content
  - Link equation to parent section/concept via `contains` edge
  - After all equations created: call `build_variable_cooccurrence()` on section's equations
  - Create `shared_variables` edges between equation pairs, with `confidence` = shared_count / max_vars, `reasoning` listing shared variable names
  - Add Phase 4: LLM classification of equation-equation relationships (optional, only for high co-occurrence pairs)

  **Must NOT do**:
  - Do NOT create variable-level nodes (Level 5 deferred)
  - Do NOT use NetworkX
  - Do NOT crash on unparseable equations (skip with is_parseable=False)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 7)
  - **Blocks**: Tasks 9, 10
  - **Blocked By**: Tasks 1, 2, 3

  **Acceptance Criteria**:
  - [ ] Equation nodes created with level='equation'
  - [ ] metadata_json contains variables list and raw_latex
  - [ ] shared_variables edges connect equations sharing symbols
  - [ ] Unparseable equations skipped (not crashed)
  - [ ] `cd backend && python -m pytest tests/test_knowledge_graph_builder.py -v` passes

  **QA Scenarios**:
  ```
  Scenario: Equation nodes with shared variables
    Tool: Bash (pytest)
    Steps:
      1. Seed 3 equations sharing variable omega_c into extracted_content
      2. Run equation node creation phase
      3. Verify 3 equation nodes exist with variables in metadata
      4. Verify shared_variables edges connect the pairs sharing omega_c
    Expected Result: Nodes + edges created deterministically
    Evidence: .sisyphus/evidence/task-6-equation-nodes.txt
  ```

  **Commit**: YES (groups with Tasks 5, 7)

- [x] 7. Concept Deduplication Logic

  **What to do**:
  - Add `_deduplicate_concept(self, textbook_id, title, new_data) -> str` to KnowledgeGraphBuilder
  - Before creating any concept node: check if a node with same title + textbook_id already exists
  - If exists: update metadata_json to merge section references, return existing node_id
  - If not: create new node, return new node_id
  - Apply dedup to both per-section LLM extraction and chapter-level extraction

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6)
  - **Blocks**: Task 12
  - **Blocked By**: Tasks 3, 5

  **Acceptance Criteria**:
  - [ ] Same concept title in 2 sections creates only 1 node
  - [ ] Metadata has both section references
  - [ ] Tests verify dedup behavior

  **QA Scenarios**:
  ```
  Scenario: Dedup merges same concept across sections
    Tool: Bash (pytest)
    Steps:
      1. Create concept "Critical Speed" in section A and section B
      2. Verify only 1 node exists with title "Critical Speed"
      3. Verify metadata_json contains references to both sections
    Expected Result: 1 node, merged metadata
    Evidence: .sisyphus/evidence/task-7-dedup.txt
  ```

  **Commit**: YES (groups with Tasks 5, 6)

- [x] 8. EquationNode KaTeX Rendering Update

  **What to do**:
  - Update `frontend/src/components/graph/EquationNode.tsx` to read `raw_latex` from node metadata
  - Render LaTeX via `InlineMath` or `BlockMath` from react-katex (already installed)
  - Show variable count badge: "{N} variables"
  - Smaller node size for equations (already configured in dagre: 160x50)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 9, 10, 11)
  - **Blocks**: Task 12
  - **Blocked By**: Task 3

  **Acceptance Criteria**:
  - [ ] Equation nodes render LaTeX content
  - [ ] Variable count badge visible
  - [ ] `cd frontend && npx tsc --noEmit` passes
  - [ ] `cd frontend && npx vitest run src/components/graph/EquationNode.test.tsx` passes

  **QA Scenarios**:
  ```
  Scenario: EquationNode renders LaTeX
    Tool: Bash (vitest)
    Steps:
      1. Render EquationNode with data containing metadata.raw_latex = "\\omega_c = \\sqrt{g/y}"
      2. Assert KaTeX element is present in rendered output
      3. cd frontend && npx vitest run src/components/graph/EquationNode.test.tsx
    Expected Result: Tests pass, LaTeX renders
    Evidence: .sisyphus/evidence/task-8-equation-render.txt
  ```

  **Commit**: YES (groups with Tasks 9, 10, 11)

- [x] 9. 4-Level Expand/Collapse

  **What to do**:
  - Update `frontend/src/hooks/useExpandCollapse.ts`
  - Add section-level expand: clicking section node reveals concept/equation children
  - Track `expandedSections: Set<string>` in addition to `expandedChapters`
  - `toggleSection(nodeId)` callback
  - Apply visibility: section children hidden unless parent section expanded AND parent chapter expanded
  - Re-run dagre layout on expand/collapse

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 8, 10, 11)
  - **Blocks**: Task 12
  - **Blocked By**: Tasks 5, 6

  **Acceptance Criteria**:
  - [ ] Chapter expand reveals sections
  - [ ] Section expand reveals concepts + equations
  - [ ] Nested collapse works (collapsing chapter hides all descendants)
  - [ ] `cd frontend && npx vitest run src/hooks/useExpandCollapse.test.ts` passes

  **QA Scenarios**:
  ```
  Scenario: 4-level expand/collapse
    Tool: Bash (vitest)
    Steps:
      1. Create test graph with chapter -> section -> concept -> equation hierarchy
      2. Toggle chapter: assert section visible, concept/equation hidden
      3. Toggle section: assert concept + equation visible
      4. Toggle chapter again: assert ALL descendants hidden
    Expected Result: Nested visibility works correctly
    Evidence: .sisyphus/evidence/task-9-expand-collapse.txt
  ```

  **Commit**: YES (groups with Tasks 8, 10, 11)

- [x] 10. Edge Styling for shared_variables

  **What to do**:
  - Update `frontend/src/components/graph/edgeStyles.ts`
  - Add `shared_variables`: purple dotted line, bidirectional, label shows shared var names
  - Add `contains`: thin gray line, no arrowhead, dashed
  - Update `GraphLegend.tsx` with new types

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 8, 9, 11)
  - **Blocks**: Task 12
  - **Blocked By**: Task 6

  **Acceptance Criteria**:
  - [ ] shared_variables edges render as purple dotted
  - [ ] contains edges render as thin gray dashed
  - [ ] Legend updated
  - [ ] `cd frontend && npx vitest run src/components/graph/edgeStyles.test.ts` passes

  **QA Scenarios**:
  ```
  Scenario: New edge types have distinct styles
    Tool: Bash (vitest)
    Steps:
      1. Call getEdgeStyle('shared_variables') — assert purple stroke
      2. Call getEdgeStyle('contains') — assert gray stroke, no arrow
      3. cd frontend && npx vitest run src/components/graph/edgeStyles.test.ts
    Expected Result: Tests pass, styles distinct
    Evidence: .sisyphus/evidence/task-10-edge-styles.txt
  ```

  **Commit**: YES (groups with Tasks 8, 9, 11)

- [x] 11. Section Path Display in ConceptDetailPanel

  **What to do**:
  - Update `frontend/src/components/graph/ConceptDetailPanel.tsx`
  - Show section_path (e.g., "CH7/7.1/7.1.2") from node metadata
  - Show variables list for equation nodes
  - Show shared_variables connections for equation nodes

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 8, 9, 10)
  - **Blocks**: Task 12
  - **Blocked By**: Task 2

  **Acceptance Criteria**:
  - [ ] Section path visible in detail panel
  - [ ] Variables listed for equation nodes
  - [ ] `cd frontend && npx tsc --noEmit` passes

  **QA Scenarios**:
  ```
  Scenario: Detail panel shows section path and variables
    Tool: Bash (vitest)
    Steps:
      1. Render ConceptDetailPanel with node having metadata.section_path = "CH7/7.3"
      2. Assert "CH7/7.3" visible in panel
      3. Render with equation node having metadata.variables = ["omega_c", "g", "y"]
      4. Assert variables listed
    Expected Result: Section path and variables display correctly
    Evidence: .sisyphus/evidence/task-11-detail-panel.txt
  ```

  **Commit**: YES (groups with Tasks 8, 9, 10)

- [ ] 12. Integration Test — Full 4-Level Pipeline

  **What to do**:
  - Write `backend/tests/test_deep_graph_integration.py`
  - Test full pipeline: trigger build on textbook with extracted content, verify 4 levels of nodes, verify shared_variables edges, verify section paths
  - Mock AIRouter for LLM calls, use real extracted_content from DB
  - Verify equation nodes have variables in metadata
  - Verify concept deduplication works across sections

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Acceptance Criteria**:
  - [ ] Test creates 4 levels of nodes
  - [ ] shared_variables edges exist between equations
  - [ ] Concept dedup verified
  - [ ] `cd backend && python -m pytest tests/test_deep_graph_integration.py -v` passes

  **QA Scenarios**:
  ```
  Scenario: Full 4-level pipeline produces correct graph structure
    Tool: Bash (pytest)
    Steps:
      1. cd backend && python -m pytest tests/test_deep_graph_integration.py -v
      2. Assert all tests pass
      3. Verify output shows: chapter nodes (level=chapter), section nodes (level=section), concept nodes (level=subsection), equation nodes (level=equation)
      4. Verify shared_variables edges exist between equation pairs
    Expected Result: All tests pass, 4 levels + deterministic edges verified
    Failure Indicators: Any test failure, missing levels, no shared_variables edges
    Evidence: .sisyphus/evidence/task-12-integration.txt
  ```

  **Commit**: YES (groups with Task 13)

- [ ] 13. Manual QA — Regenerate Graph on Real Textbook

  **What to do**:
  - Start backend + frontend
  - Navigate to Mechanical Design Engineering Handbook
  - Click Regenerate
  - Verify 4-level graph renders with equation nodes showing LaTeX
  - Verify expand/collapse works across all levels
  - Verify shared_variables edges connect equations
  - Save screenshots as evidence

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`playwright`]

  **Acceptance Criteria**:
  - [ ] Graph has 50+ nodes across 4 levels
  - [ ] Equation nodes render LaTeX
  - [ ] shared_variables edges visible
  - [ ] Expand/collapse works for all levels
  - [ ] Evidence screenshots saved

  **QA Scenarios**:
  ```
  Scenario: Regenerate graph and verify 4-level rendering
    Tool: Playwright (via interactive_bash tmux for servers)
    Preconditions: Start backend (tmux qa-backend: cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000), start frontend (tmux qa-frontend: cd frontend && bun run dev)
    Steps:
      1. Delete existing graph: curl -X DELETE http://127.0.0.1:8000/api/knowledge-graph/c60841bd-095d-4f73-a6e3-b48491c129ed
      2. Trigger rebuild: curl -X POST http://127.0.0.1:8000/api/knowledge-graph/c60841bd-095d-4f73-a6e3-b48491c129ed/build
      3. Poll status until completed (timeout 120s)
      4. Verify graph data: curl http://127.0.0.1:8000/api/knowledge-graph/c60841bd-095d-4f73-a6e3-b48491c129ed/graph | python -c "import sys,json; d=json.load(sys.stdin); levels=set(n['level'] for n in d['nodes']); print(f'Levels: {levels}, Nodes: {len(d[\"nodes\"])}, Edges: {len(d[\"edges\"])}')"
      5. Assert: 4 levels present (chapter, section, subsection, equation), 50+ nodes, shared_variables edges exist
      6. Navigate Playwright to http://localhost:5173/graph/c60841bd-095d-4f73-a6e3-b48491c129ed
      7. Assert .react-flow container visible with nodes
      8. Take screenshot
    Expected Result: 4 levels, 50+ nodes, equation nodes with KaTeX, shared_variables edges
    Failure Indicators: Only 2 levels, <20 nodes, no equation nodes, no shared_variables edges
    Evidence: .sisyphus/evidence/task-13-full-qa.png
  ```
  Teardown: `tmux kill-session -t qa-backend && tmux kill-session -t qa-frontend`

  **Commit**: NO (verification only)

---

## Commit Strategy

| After Task(s) | Commit Message |
|---|---|
| 1, 2, 3, 4 | `feat(knowledge-graph): add LaTeX parser, section mapper, models, prompts` |
| 5, 6, 7 | `feat(knowledge-graph): per-section extraction, equation nodes, dedup` |
| 8, 9, 10, 11 | `feat(knowledge-graph): 4-level UI — equation KaTeX nodes, deeper expand` |
| 12, 13 | `test(knowledge-graph): integration tests for 4-level pipeline` |

---

## Success Criteria

### Verification Commands
```bash
cd backend && python -m pytest tests/ -q
cd frontend && npx vitest run
cd frontend && npx tsc --noEmit
```

### Final Checklist
- [ ] Graph produces 4 levels (chapter, section, concept, equation)
- [ ] LaTeX equations rendered in graph nodes via KaTeX
- [ ] shared_variables edges connect equations deterministically
- [ ] Per-section LLM extraction produces richer concepts than per-chapter
- [ ] All tests pass, tsc clean
