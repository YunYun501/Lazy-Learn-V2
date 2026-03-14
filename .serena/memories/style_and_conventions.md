# Code Style & Conventions

## Python (Backend)
- **Type hints**: Used on function signatures (return types, parameters)
- **Docstrings**: Triple-quoted, present on public methods/classes
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Async**: All DB operations and AI calls are async/await
- **Models**: Pydantic BaseModel for request/response validation
- **Imports**: Standard lib → third-party → local app imports
- **String formatting**: f-strings preferred
- **Optional types**: `Optional[T]` from typing, or `T | None`

## TypeScript (Frontend)
- **Framework**: React with functional components + hooks
- **State**: useState/useEffect patterns, no global state library
- **API calls**: Custom api/ modules per domain (chapters.ts, courses.ts, etc.)
- **Styling**: CSS files in styles/ directory
- **Components**: PascalCase, one component per file

## Project Patterns
- Factory functions for dependencies (get_storage(), get_filesystem())
- Background tasks via FastAPI BackgroundTasks
- SSE streaming for AI responses (explain endpoint)
- SQLite with raw SQL (no ORM)
- UUID-based IDs for all entities
