# Task Completion Checklist

When finishing a task, verify:

1. **Tests pass**: `cd backend && python -m pytest tests/ -v`
2. **No type errors**: Check with IDE/LSP diagnostics
3. **Backend starts**: `python -m uvicorn app.main:app --port 8000` without errors
4. **Frontend builds**: `cd frontend && npm run build` without errors
5. **Existing patterns followed**: Match the style in style_and_conventions memory
6. **No hardcoded secrets**: API keys go through SettingsStore or .env
7. **Database migrations**: If schema changed, update CREATE_TABLES_SQL and MIGRATE_* in storage.py
