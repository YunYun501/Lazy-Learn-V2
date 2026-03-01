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

CREATE TABLE IF NOT EXISTS university_materials (
    id TEXT PRIMARY KEY,
    course_id TEXT NOT NULL,
    title TEXT NOT NULL,
    file_type TEXT NOT NULL,
    filepath TEXT NOT NULL,
    created_at TEXT NOT NULL
);
""";

MIGRATE_V2_SQL = """
CREATE TABLE IF NOT EXISTS sections (
    id TEXT PRIMARY KEY,
    chapter_id TEXT NOT NULL,
    section_number INTEGER,
    title TEXT,
    page_start INTEGER,
    page_end INTEGER
);

CREATE TABLE IF NOT EXISTS extracted_content (
    id TEXT PRIMARY KEY,
    chapter_id TEXT NOT NULL,
    content_type TEXT NOT NULL,
    title TEXT,
    content TEXT,
    file_path TEXT,
    page_number INTEGER,
    order_index INTEGER
);

CREATE TABLE IF NOT EXISTS material_summaries (
    id TEXT PRIMARY KEY,
    material_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    summary_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            
            # Call v2 migration
            await self._migrate_v2(db)
            
            # Add course_id column to textbooks if missing (idempotent migration)
            try:
                await db.execute("ALTER TABLE textbooks ADD COLUMN course_id TEXT")
                await db.commit()
            except Exception:
                pass  # Column already exists
            
            # Auto-create Math Library reserved course
            await db.execute(
                "INSERT OR IGNORE INTO courses (id, name, created_at) VALUES (?, ?, ?)",
                (str(uuid.uuid4()), "Math Library", datetime.utcnow().isoformat())
            )
            await db.commit()
    
    async def _migrate_v2(self, db):
        """Apply v2 schema migrations: new tables and columns."""
        # Create new tables
        await db.executescript(MIGRATE_V2_SQL)
        await db.commit()
        
        # Add extraction_status column to chapters if missing
        try:
            await db.execute("ALTER TABLE chapters ADD COLUMN extraction_status TEXT DEFAULT 'pending'")
            await db.commit()
        except Exception:
            pass  # Column already exists
        
        # Add pipeline_status column to textbooks if missing
        try:
            await db.execute("ALTER TABLE textbooks ADD COLUMN pipeline_status TEXT DEFAULT 'uploaded'")
            await db.commit()
        except Exception:
            pass  # Column already exists

        # Add parent_section_id and level columns to sections if missing
        try:
            await db.execute("ALTER TABLE sections ADD COLUMN parent_section_id TEXT")
            await db.commit()
        except Exception:
            pass  # Column already exists
        try:
            await db.execute("ALTER TABLE sections ADD COLUMN level INTEGER DEFAULT 2")
            await db.commit()
        except Exception:
            pass  # Column already exists

    # --- Textbooks ---

    async def create_textbook(
        self,
        title: str,
        filepath: str,
        course: Optional[str] = None,
        library_type: str = "course",
        textbook_id: Optional[str] = None,
    ) -> str:
        """Create a textbook record. Returns the textbook ID."""
        if textbook_id is None:
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

    async def delete_textbook(self, textbook_id: str):
        """Delete a textbook and all its chapters from the database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM chapters WHERE textbook_id = ?", (textbook_id,))
            await db.execute("DELETE FROM textbooks WHERE id = ?", (textbook_id,))
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

    async def get_course(self, course_id: str) -> Optional[dict]:
        """Get a single course by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def update_course(self, course_id: str, name: str) -> dict:
        """Update course name. Raises ValueError if name taken."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute(
                "UPDATE courses SET name = ? WHERE id = ?",
                (name, course_id)
            )
            await db.commit()
            async with db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row)

    async def delete_course(self, course_id: str) -> None:
        """Cascade delete: disk files → chapters → textbooks → university_materials → course."""
        import shutil
        from pathlib import Path
        
        # Get textbooks to delete files on disk
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT id, filepath FROM textbooks WHERE course_id = ?", (course_id,)) as cursor:
                textbooks = [dict(row) async for row in cursor]
            
            # Delete files on disk for each textbook
            for tb in textbooks:
                tb_dir = Path("data") / "textbooks" / tb['id']
                if tb_dir.exists():
                    shutil.rmtree(tb_dir)
                desc_dir = Path("data") / "descriptions" / tb['id']
                if desc_dir.exists():
                    shutil.rmtree(desc_dir)
            
            # Delete university material files
            async with db.execute("SELECT filepath FROM university_materials WHERE course_id = ?", (course_id,)) as cursor:
                materials = [dict(row) async for row in cursor]
            for mat in materials:
                mat_path = Path(mat['filepath'])
                if mat_path.exists():
                    mat_path.unlink()
            
            # Delete DB records in dependency order
            textbook_ids = [tb['id'] for tb in textbooks]
            for tb_id in textbook_ids:
                await db.execute("DELETE FROM chapters WHERE textbook_id = ?", (tb_id,))
            await db.execute("DELETE FROM textbooks WHERE course_id = ?", (course_id,))
            await db.execute("DELETE FROM university_materials WHERE course_id = ?", (course_id,))
            await db.execute("DELETE FROM courses WHERE id = ?", (course_id,))
            await db.commit()

    async def assign_textbook_to_course(self, textbook_id: str, course_id: str) -> None:
        """Assign a textbook to a course (set course_id FK)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE textbooks SET course_id = ? WHERE id = ?",
                (course_id, textbook_id)
            )
            await db.commit()

    async def get_course_textbooks(self, course_id: str) -> list[dict]:
        """Get all textbooks belonging to a course."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM textbooks WHERE course_id = ?", (course_id,)) as cursor:
                return [dict(row) async for row in cursor]

    async def create_university_material(self, course_id: str, title: str, file_type: str, filepath: str) -> dict:
        """Store a university material record."""
        material_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO university_materials (id, course_id, title, file_type, filepath, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (material_id, course_id, title, file_type, filepath, created_at)
            )
            await db.commit()
        return {"id": material_id, "course_id": course_id, "title": title, "file_type": file_type, "filepath": filepath, "created_at": created_at}

    async def get_university_material(self, material_id: str) -> Optional[dict]:
        """Get a single university material by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM university_materials WHERE id = ?", (material_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    async def list_university_materials(self, course_id: str) -> list[dict]:
        """List all university materials for a course."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM university_materials WHERE course_id = ?", (course_id,)) as cursor:
                return [dict(row) async for row in cursor]

    async def delete_university_material(self, material_id: str) -> None:
        """Delete a university material record (caller handles file deletion)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM university_materials WHERE id = ?", (material_id,))
            await db.commit()

    # --- Conversations ---

    async def create_conversation(
        self,
        conversation_id: str,
        query: str,
        course_id: Optional[str] = None,
    ) -> str:
        """Create a conversation record. Returns the conversation ID."""
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO conversations (id, course_id, query, created_at) VALUES (?, ?, ?, ?)",
                (conversation_id, course_id, query, now),
            )
            await db.commit()
        return conversation_id

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> str:
        """Append a message to a conversation. Returns the message ID."""
        message_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (message_id, conversation_id, role, content, now),
            )
            await db.commit()
        return message_id

    async def get_messages(self, conversation_id: str) -> list[dict]:
        """Retrieve all messages for a conversation in chronological order."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at",
                (conversation_id,),
            ) as cursor:
                rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # --- Sections (v2) ---
    
    async def create_section(self, section_data: dict) -> str:
        """Create a section record. Returns the section ID."""
        section_id = str(uuid.uuid4())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO sections (id, chapter_id, section_number, title, page_start, page_end, parent_section_id, level) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (section_id, section_data['chapter_id'], section_data.get('section_number'), section_data.get('title'), section_data.get('page_start'), section_data.get('page_end'), section_data.get('parent_section_id'), section_data.get('level', 2)),
            )
            await db.commit()
        return section_id
    
    async def get_sections_for_chapter(self, chapter_id: str) -> list[dict]:
        """Get all sections for a chapter."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM sections WHERE chapter_id = ? AND (parent_section_id IS NULL OR parent_section_id = '') ORDER BY section_number",
                (chapter_id,),
            ) as cursor:
                rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_subsections_for_section(self, section_id: str) -> list[dict]:
        """Get all sub-sections (level 3) for a parent section."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM sections WHERE parent_section_id = ? ORDER BY section_number",
                (section_id,),
            ) as cursor:
                rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # --- Extracted Content (v2) ---
    
    async def create_extracted_content(self, content_data: dict) -> str:
        """Create an extracted content record. Returns the content ID."""
        content_id = str(uuid.uuid4())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO extracted_content (id, chapter_id, content_type, title, content, file_path, page_number, order_index) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (content_id, content_data['chapter_id'], content_data['content_type'], content_data.get('title'), content_data.get('content'), content_data.get('file_path'), content_data.get('page_number'), content_data.get('order_index')),
            )
            await db.commit()
        return content_id
    
    async def get_extracted_content_for_chapter(self, chapter_id: str) -> list[dict]:
        """Get all extracted content for a chapter."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM extracted_content WHERE chapter_id = ? ORDER BY order_index",
                (chapter_id,),
            ) as cursor:
                rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # --- Material Summaries (v2) ---
    
    async def create_material_summary(self, summary_data: dict) -> str:
        """Create or replace a material summary record. Returns the summary ID."""
        material_id = summary_data['material_id']
        async with aiosqlite.connect(self.db_path) as db:
            # Check if summary already exists
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id FROM material_summaries WHERE material_id = ?",
                (material_id,),
            ) as cursor:
                existing = await cursor.fetchone()
            
            if existing:
                # Update existing summary
                summary_id = existing['id']
                await db.execute(
                    "UPDATE material_summaries SET course_id = ?, summary_json = ?, created_at = ? WHERE material_id = ?",
                    (summary_data['course_id'], summary_data.get('summary_json'), datetime.utcnow().isoformat(), material_id),
                )
            else:
                # Create new summary
                summary_id = str(uuid.uuid4())
                await db.execute(
                    "INSERT INTO material_summaries (id, material_id, course_id, summary_json, created_at) VALUES (?, ?, ?, ?, ?)",
                    (summary_id, material_id, summary_data['course_id'], summary_data.get('summary_json'), datetime.utcnow().isoformat()),
                )
            await db.commit()
        return summary_id
    
    async def get_material_summary(self, material_id: str) -> Optional[dict]:
        """Get a material summary by material_id."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM material_summaries WHERE material_id = ?",
                (material_id,),
            ) as cursor:
                row = await cursor.fetchone()
            return dict(row) if row else None
    
    # --- Status Updates (v2) ---
    
    async def update_chapter_extraction_status(self, chapter_id: str, status: str) -> None:
        """Update extraction_status for a chapter."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE chapters SET extraction_status = ? WHERE id = ?",
                (status, chapter_id),
            )
            await db.commit()
    
    async def update_textbook_pipeline_status(self, textbook_id: str, status: str) -> None:
        """Update pipeline_status for a textbook."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE textbooks SET pipeline_status = ? WHERE id = ?",
                (status, textbook_id),
            )
            await db.commit()
    
    async def get_chapters_by_extraction_status(self, textbook_id: str, status: str) -> list[dict]:
        """Get all chapters for a textbook with a specific extraction_status."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM chapters WHERE textbook_id = ? AND extraction_status = ? ORDER BY page_start",
                (textbook_id, status),
            ) as cursor:
                rows = await cursor.fetchall()
            return [dict(row) for row in rows]
