# Decisions

## [2026-03-16] Core Architecture Decisions (from planning session)

- **Visualization**: React Flow (@xyflow/react) — native React, custom nodes
- **Scope**: Per-textbook MVP. Cross-textbook deferred.
- **Trigger**: On-demand — "Generate Relationship" button click
- **Storage**: Extend SQLite with new tables (concept_nodes + concept_edges + graph_generation_jobs)
- **LLM**: Use existing AIRouter (DeepSeek primary, OpenAI fallback)
- **Granularity**: Multi-level expandable (chapter → section → equation)
- **Display**: Dedicated new page `/graph/:textbookId`
- **Node click**: Show concept details panel
- **Relationship types**: derives_from, proves, prerequisite_of, uses, generalizes, specializes, contradicts, defines, equivalent_form (9 total)
- **Tests**: TDD (pytest-asyncio backend, vitest frontend)
- **Graph layout**: Dagre (`@dagrejs/dagre`) with rankdir=TB
- **Node visual distinction**: theorem=pink, definition=amber, equation=text-accent; edge styles by type

## [2026-03-16] useExpandCollapse hook
- No new decisions.
