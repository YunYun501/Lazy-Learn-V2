import pytest
import aiosqlite
from pathlib import Path
from app.services.storage import MetadataStore


@pytest.fixture
async def store(tmp_path):
    """Create a MetadataStore with a temporary database."""
    db_path = tmp_path / "test.db"
    store = MetadataStore(db_path=db_path)
    await store.initialize()
    return store


@pytest.mark.asyncio
async def test_sections_table_created(store):
    """PRAGMA table_info(sections) returns all expected columns."""
    async with aiosqlite.connect(store.db_path) as db:
        async with db.execute("PRAGMA table_info(sections)") as cursor:
            columns = await cursor.fetchall()
    
    column_names = [col[1] for col in columns]
    assert 'id' in column_names
    assert 'chapter_id' in column_names
    assert 'section_number' in column_names
    assert 'title' in column_names
    assert 'page_start' in column_names
    assert 'page_end' in column_names


@pytest.mark.asyncio
async def test_extracted_content_table_created(store):
    """PRAGMA table_info(extracted_content) returns all expected columns."""
    async with aiosqlite.connect(store.db_path) as db:
        async with db.execute("PRAGMA table_info(extracted_content)") as cursor:
            columns = await cursor.fetchall()
    
    column_names = [col[1] for col in columns]
    assert 'id' in column_names
    assert 'chapter_id' in column_names
    assert 'content_type' in column_names
    assert 'title' in column_names
    assert 'content' in column_names
    assert 'file_path' in column_names
    assert 'page_number' in column_names
    assert 'order_index' in column_names


@pytest.mark.asyncio
async def test_material_summaries_table_created(store):
    """PRAGMA table_info(material_summaries) returns all expected columns."""
    async with aiosqlite.connect(store.db_path) as db:
        async with db.execute("PRAGMA table_info(material_summaries)") as cursor:
            columns = await cursor.fetchall()
    
    column_names = [col[1] for col in columns]
    assert 'id' in column_names
    assert 'material_id' in column_names
    assert 'course_id' in column_names
    assert 'summary_json' in column_names
    assert 'created_at' in column_names


@pytest.mark.asyncio
async def test_chapters_extraction_status_column_added(store):
    """PRAGMA table_info(chapters) contains extraction_status column."""
    async with aiosqlite.connect(store.db_path) as db:
        async with db.execute("PRAGMA table_info(chapters)") as cursor:
            columns = await cursor.fetchall()
    
    column_names = [col[1] for col in columns]
    assert 'extraction_status' in column_names


@pytest.mark.asyncio
async def test_textbooks_pipeline_status_column_added(store):
    """PRAGMA table_info(textbooks) contains pipeline_status column."""
    async with aiosqlite.connect(store.db_path) as db:
        async with db.execute("PRAGMA table_info(textbooks)") as cursor:
            columns = await cursor.fetchall()
    
    column_names = [col[1] for col in columns]
    assert 'pipeline_status' in column_names


@pytest.mark.asyncio
async def test_create_section_and_get_sections_for_chapter(store):
    """create_section() inserts and returns id; get_sections_for_chapter() retrieves by chapter_id."""
    # Create a textbook and chapter first
    textbook_id = await store.create_textbook(
        title="Test Book",
        filepath="/path/to/book.pdf"
    )
    chapter_id = await store.create_chapter(
        textbook_id=textbook_id,
        chapter_number="1",
        title="Chapter 1",
        page_start=1,
        page_end=50
    )
    
    # Create sections
    section_data_1 = {
        "chapter_id": chapter_id,
        "section_number": 1,
        "title": "Section 1.1",
        "page_start": 1,
        "page_end": 20
    }
    section_id_1 = await store.create_section(section_data_1)
    assert section_id_1 is not None
    
    section_data_2 = {
        "chapter_id": chapter_id,
        "section_number": 2,
        "title": "Section 1.2",
        "page_start": 21,
        "page_end": 50
    }
    section_id_2 = await store.create_section(section_data_2)
    assert section_id_2 is not None
    
    # Get sections for chapter
    sections = await store.get_sections_for_chapter(chapter_id)
    assert len(sections) == 2
    assert sections[0]['title'] == "Section 1.1"
    assert sections[1]['title'] == "Section 1.2"


@pytest.mark.asyncio
async def test_create_extracted_content_and_get_for_chapter(store):
    """create_extracted_content() inserts and returns id; get_extracted_content_for_chapter() retrieves by chapter_id."""
    # Create a textbook and chapter first
    textbook_id = await store.create_textbook(
        title="Test Book",
        filepath="/path/to/book.pdf"
    )
    chapter_id = await store.create_chapter(
        textbook_id=textbook_id,
        chapter_number="1",
        title="Chapter 1",
        page_start=1,
        page_end=50
    )
    
    # Create extracted content
    content_data_1 = {
        "chapter_id": chapter_id,
        "content_type": "text",
        "title": "Introduction",
        "content": "This is the introduction...",
        "file_path": "/path/to/intro.txt",
        "page_number": 1,
        "order_index": 0
    }
    content_id_1 = await store.create_extracted_content(content_data_1)
    assert content_id_1 is not None
    
    content_data_2 = {
        "chapter_id": chapter_id,
        "content_type": "image",
        "title": "Figure 1",
        "content": "image_data",
        "file_path": "/path/to/figure1.png",
        "page_number": 5,
        "order_index": 1
    }
    content_id_2 = await store.create_extracted_content(content_data_2)
    assert content_id_2 is not None
    
    # Get extracted content for chapter
    contents = await store.get_extracted_content_for_chapter(chapter_id)
    assert len(contents) == 2
    assert contents[0]['content_type'] == "text"
    assert contents[1]['content_type'] == "image"


@pytest.mark.asyncio
async def test_material_summary_crud(store):
    """create_material_summary() inserts/replaces and returns id; get_material_summary() retrieves by material_id."""
    # Create a course and university material first
    course_id = await store.create_course("Test Course")
    material = await store.create_university_material(
        course_id=course_id,
        title="Lecture Notes",
        file_type="pdf",
        filepath="/path/to/notes.pdf"
    )
    material_id = material['id']
    
    # Create material summary
    summary_data = {
        "material_id": material_id,
        "course_id": course_id,
        "summary_json": '{"key": "value", "topics": ["topic1", "topic2"]}'
    }
    summary_id = await store.create_material_summary(summary_data)
    assert summary_id is not None
    
    # Get material summary
    summary = await store.get_material_summary(material_id)
    assert summary is not None
    assert summary['material_id'] == material_id
    assert summary['course_id'] == course_id
    assert '"key": "value"' in summary['summary_json']
    
    # Update summary (INSERT OR REPLACE)
    updated_summary_data = {
        "material_id": material_id,
        "course_id": course_id,
        "summary_json": '{"key": "updated_value"}'
    }
    updated_id = await store.create_material_summary(updated_summary_data)
    assert updated_id == summary_id  # Same ID
    
    # Verify update
    updated = await store.get_material_summary(material_id)
    assert '"key": "updated_value"' in updated['summary_json']


@pytest.mark.asyncio
async def test_update_chapter_extraction_status(store):
    """update_chapter_extraction_status() updates extraction_status column."""
    # Create a textbook and chapter
    textbook_id = await store.create_textbook(
        title="Test Book",
        filepath="/path/to/book.pdf"
    )
    chapter_id = await store.create_chapter(
        textbook_id=textbook_id,
        chapter_number="1",
        title="Chapter 1",
        page_start=1,
        page_end=50
    )
    
    # Update extraction status
    await store.update_chapter_extraction_status(chapter_id, "processing")
    
    # Verify
    async with aiosqlite.connect(store.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT extraction_status FROM chapters WHERE id = ?", (chapter_id,)) as cursor:
            row = await cursor.fetchone()
    
    assert row['extraction_status'] == "processing"


@pytest.mark.asyncio
async def test_update_textbook_pipeline_status(store):
    """update_textbook_pipeline_status() updates pipeline_status column."""
    # Create a textbook
    textbook_id = await store.create_textbook(
        title="Test Book",
        filepath="/path/to/book.pdf"
    )
    
    # Update pipeline status
    await store.update_textbook_pipeline_status(textbook_id, "processing")
    
    # Verify
    async with aiosqlite.connect(store.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT pipeline_status FROM textbooks WHERE id = ?", (textbook_id,)) as cursor:
            row = await cursor.fetchone()
    
    assert row['pipeline_status'] == "processing"


@pytest.mark.asyncio
async def test_get_chapters_by_extraction_status(store):
    """get_chapters_by_extraction_status() retrieves chapters by textbook_id and status."""
    # Create a textbook
    textbook_id = await store.create_textbook(
        title="Test Book",
        filepath="/path/to/book.pdf"
    )
    
    # Create chapters with different statuses
    chapter_id_1 = await store.create_chapter(
        textbook_id=textbook_id,
        chapter_number="1",
        title="Chapter 1",
        page_start=1,
        page_end=50
    )
    await store.update_chapter_extraction_status(chapter_id_1, "pending")
    
    chapter_id_2 = await store.create_chapter(
        textbook_id=textbook_id,
        chapter_number="2",
        title="Chapter 2",
        page_start=51,
        page_end=100
    )
    await store.update_chapter_extraction_status(chapter_id_2, "completed")
    
    chapter_id_3 = await store.create_chapter(
        textbook_id=textbook_id,
        chapter_number="3",
        title="Chapter 3",
        page_start=101,
        page_end=150
    )
    await store.update_chapter_extraction_status(chapter_id_3, "pending")
    
    # Get chapters by status
    pending_chapters = await store.get_chapters_by_extraction_status(textbook_id, "pending")
    assert len(pending_chapters) == 2
    assert pending_chapters[0]['title'] == "Chapter 1"
    assert pending_chapters[1]['title'] == "Chapter 3"
    
    completed_chapters = await store.get_chapters_by_extraction_status(textbook_id, "completed")
    assert len(completed_chapters) == 1
    assert completed_chapters[0]['title'] == "Chapter 2"


@pytest.mark.asyncio
async def test_initialize_idempotent_v2(tmp_path):
    """Call initialize() twice, no errors. Verify new tables and columns exist."""
    db_path = tmp_path / "test.db"
    store = MetadataStore(db_path=db_path)
    
    # First initialization
    await store.initialize()
    
    # Second initialization should not raise
    await store.initialize()
    
    # Verify all new tables exist
    async with aiosqlite.connect(store.db_path) as db:
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('sections', 'extracted_content', 'material_summaries')") as cursor:
            tables = await cursor.fetchall()
    
    table_names = [t[0] for t in tables]
    assert 'sections' in table_names
    assert 'extracted_content' in table_names
    assert 'material_summaries' in table_names
    
    # Verify new columns exist
    async with aiosqlite.connect(store.db_path) as db:
        async with db.execute("PRAGMA table_info(chapters)") as cursor:
            columns = await cursor.fetchall()
    
    column_names = [col[1] for col in columns]
    assert 'extraction_status' in column_names
    
    async with aiosqlite.connect(store.db_path) as db:
        async with db.execute("PRAGMA table_info(textbooks)") as cursor:
            columns = await cursor.fetchall()
    
    column_names = [col[1] for col in columns]
    assert 'pipeline_status' in column_names
