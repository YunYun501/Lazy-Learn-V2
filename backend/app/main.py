from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import textbooks, descriptions, search, explain, practice, conversations, organize, settings, lms

app = FastAPI(title="Lazy Learn Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:1420", "tauri://localhost"],
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

@app.get("/health")
async def health():
    return {"status": "ok"}
