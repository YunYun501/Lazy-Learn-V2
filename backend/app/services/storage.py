import aiosqlite
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path("data/lazy_learn.db")

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS courses (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS textbooks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    filepath TEXT NOT NULL,
    course TEXT,
    library_type TEXT NOT NULL DEFAULT 'course',
    processed_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chapters (
    id TEXT PRIMARY KEY,
    textbook_id TEXT NOT NULL,
    chapter_number TEXT NOT NULL,
    title TEXT NOT NULL,
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    description_path TEXT,
    FOREIGN KEY (textbook_id) REFERENCES textbooks(id)
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    course_id TEXT,
    query TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
"""

class MetadataStore:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path

    async def initialize(self):
        """Create tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(CREATE_TABLES_SQL)
            await db.commit()

    # --- Textbooks ---

    async def create_textbook(
        self,
        title: str,
        filepath: str,
        course: Optional[str] = None,
        library_type: str = "course",
    ) -> str:
        """Create a textbook record. Returns the new textbook ID."""
        textbook_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO textbooks (id, title, filepath, course, library_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (textbook_id, title, filepath, course, library_type, now),
            )
            await db.commit()
        return textbook_id

    async def get_textbook(self, textbook_id: str) -> Optional[dict]:
        """Get a textbook by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM textbooks WHERE id = ?", (textbook_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def list_textbooks(self, course: Optional[str] = None) -> list[dict]:
        """List all textbooks, optionally filtered by course."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if course:
                async with db.execute(
                    "SELECT * FROM textbooks WHERE course = ? ORDER BY created_at", (course,)
                ) as cursor:
                    rows = await cursor.fetchall()
            else:
                async with db.execute(
                    "SELECT * FROM textbooks ORDER BY created_at"
                ) as cursor:
                    rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def mark_textbook_processed(self, textbook_id: str):
        """Mark a textbook as processed."""
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE textbooks SET processed_at = ? WHERE id = ?",
                (now, textbook_id),
            )
            await db.commit()

    # --- Chapters ---

    async def create_chapter(
        self,
        textbook_id: str,
        chapter_number: str,
        title: str,
        page_start: int,
        page_end: int,
        description_path: Optional[str] = None,
    ) -> str:
        """Create a chapter record. Returns the new chapter ID."""
        chapter_id = str(uuid.uuid4())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO chapters (id, textbook_id, chapter_number, title, page_start, page_end, description_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (chapter_id, textbook_id, chapter_number, title, page_start, page_end, description_path),
            )
            await db.commit()
        return chapter_id

    async def list_chapters(self, textbook_id: str) -> list[dict]:
        """List all chapters for a textbook."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM chapters WHERE textbook_id = ? ORDER BY page_start",
                (textbook_id,),
            ) as cursor:
                rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # --- Courses ---

    async def create_course(self, name: str) -> str:
        """Create a course. Returns the course ID."""
        course_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO courses (id, name, created_at) VALUES (?, ?, ?)",
                (course_id, name, now),
            )
            await db.commit()
        return course_id

    async def list_courses(self) -> list[dict]:
        """List all courses."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM courses ORDER BY name") as cursor:
                rows = await cursor.fetchall()
            return [dict(row) for row in rows]
