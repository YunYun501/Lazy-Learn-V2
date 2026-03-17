from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings as app_settings
from app.core.logging_config import setup_logging
from app.middleware.request_logging import RequestLoggingMiddleware
from app.routers import (
    textbooks,
    descriptions,
    search,
    explain,
    practice,
    conversations,
    organize,
    settings,
    lms,
    courses,
    university_materials,
    knowledge_graph,
    logs,
)

setup_logging(log_level=app_settings.LOG_LEVEL, log_dir=app_settings.LOG_DIR)

app = FastAPI(title="Lazy Learn Backend", version="0.1.0")

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "tauri://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(textbooks.router)
app.include_router(descriptions.router)
app.include_router(search.router)
app.include_router(explain.router)
app.include_router(practice.router)
app.include_router(conversations.router)
app.include_router(organize.router)
app.include_router(settings.router)
app.include_router(lms.router)
app.include_router(courses.router)
app.include_router(university_materials.router)
app.include_router(knowledge_graph.router)
app.include_router(logs.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
