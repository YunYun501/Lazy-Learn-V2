# Suggested Commands

## Running the App
```bash
python run.py                    # Start both backend + frontend
```

## Backend Only
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Frontend Only
```bash
cd frontend
npm run dev
```

## Testing
```bash
cd backend
python -m pytest tests/ -v                    # All tests
python -m pytest tests/test_storage.py -v     # Single file
python -m pytest tests/ -k "test_name" -v     # Single test
```

## Tauri Desktop Build
```bash
cd src-tauri
cargo tauri dev      # Dev mode
cargo tauri build    # Production build
```

## Code Intelligence
```bash
npx gitnexus analyze    # Reindex codebase
npx gitnexus status     # Check index freshness
```

## System Utilities (Windows/Git Bash)
```bash
ls, cat, grep, find     # Git Bash provides unix commands
git status/diff/log     # Git operations
pip install -e .        # Install backend in editable mode
npm install             # Install frontend dependencies
```
