import pytest
import tempfile
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
async def test_initialize_idempotent(tmp_path):
    """Call initialize() twice, no error."""
    db_path = tmp_path / "test.db"
    store = MetadataStore(db_path=db_path)
    
    # First initialization
    await store.initialize()
    
    # Second initialization should not raise
    await store.initialize()
    
    # Verify Math Library exists
    courses = await store.list_courses()
    math_lib = [c for c in courses if c['name'] == 'Math Library']
    assert len(math_lib) == 1


@pytest.mark.asyncio
async def test_university_materials_table_created(store):
    """PRAGMA table_info(university_materials) returns columns."""
    import aiosqlite
    
    async with aiosqlite.connect(store.db_path) as db:
        async with db.execute("PRAGMA table_info(university_materials)") as cursor:
            columns = await cursor.fetchall()
    
    column_names = [col[1] for col in columns]
    assert 'id' in column_names
    assert 'course_id' in column_names
    assert 'title' in column_names
    assert 'file_type' in column_names
    assert 'filepath' in column_names
    assert 'created_at' in column_names


@pytest.mark.asyncio
async def test_course_id_column_exists_on_textbooks(store):
    """PRAGMA table_info(textbooks) contains course_id."""
    import aiosqlite
    
    async with aiosqlite.connect(store.db_path) as db:
        async with db.execute("PRAGMA table_info(textbooks)") as cursor:
            columns = await cursor.fetchall()
    
    column_names = [col[1] for col in columns]
    assert 'course_id' in column_names


@pytest.mark.asyncio
async def test_math_library_auto_created(store):
    """After initialize(), list_courses() contains 'Math Library'."""
    courses = await store.list_courses()
    course_names = [c['name'] for c in courses]
    assert 'Math Library' in course_names


@pytest.mark.asyncio
async def test_math_library_only_created_once(tmp_path):
    """initialize() twice, still only one 'Math Library'."""
    db_path = tmp_path / "test.db"
    store = MetadataStore(db_path=db_path)
    
    await store.initialize()
    await store.initialize()
    
    courses = await store.list_courses()
    math_libs = [c for c in courses if c['name'] == 'Math Library']
    assert len(math_libs) == 1


@pytest.mark.asyncio
async def test_university_material_crud(store):
    """Create, list, delete operations."""
    # Create a course
    course_id = await store.create_course("Test Course")
    
    # Create university material
    material = await store.create_university_material(
        course_id=course_id,
        title="Lecture Notes",
        file_type="pdf",
        filepath="/path/to/notes.pdf"
    )
    assert material['id'] is not None
    assert material['course_id'] == course_id
    assert material['title'] == "Lecture Notes"
    
    # List materials
    materials = await store.list_university_materials(course_id)
    assert len(materials) == 1
    assert materials[0]['title'] == "Lecture Notes"
    
    # Delete material
    await store.delete_university_material(material['id'])
    materials = await store.list_university_materials(course_id)
    assert len(materials) == 0


@pytest.mark.asyncio
async def test_get_course(store):
    """Create course, get_course by id returns it."""
    course_id = await store.create_course("Advanced Math")
    
    course = await store.get_course(course_id)
    assert course is not None
    assert course['id'] == course_id
    assert course['name'] == "Advanced Math"


@pytest.mark.asyncio
async def test_update_course(store):
    """Create course, update_course, verify name changed."""
    course_id = await store.create_course("Original Name")
    
    updated = await store.update_course(course_id, "Updated Name")
    assert updated['name'] == "Updated Name"
    
    # Verify in database
    course = await store.get_course(course_id)
    assert course['name'] == "Updated Name"


@pytest.mark.asyncio
async def test_cascade_delete(store, tmp_path):
    """Create course + textbook (with course_id) + university_material, delete_course, verify all gone."""
    # Create course
    course_id = await store.create_course("Delete Test Course")
    
    # Create textbook with course_id
    textbook_id = await store.create_textbook(
        title="Test Textbook",
        filepath="/path/to/textbook.pdf"
    )
    await store.assign_textbook_to_course(textbook_id, course_id)
    
    # Create chapter
    chapter_id = await store.create_chapter(
        textbook_id=textbook_id,
        chapter_number="1",
        title="Chapter 1",
        page_start=1,
        page_end=10
    )
    
    # Create university material
    material = await store.create_university_material(
        course_id=course_id,
        title="Material",
        file_type="pdf",
        filepath=str(tmp_path / "material.pdf")
    )
    # Create the file so it can be deleted
    Path(material['filepath']).touch()
    
    # Delete course
    await store.delete_course(course_id)
    
    # Verify all gone
    course = await store.get_course(course_id)
    assert course is None
    
    textbook = await store.get_textbook(textbook_id)
    assert textbook is None
    
    chapters = await store.list_chapters(textbook_id)
    assert len(chapters) == 0
    
    materials = await store.list_university_materials(course_id)
    assert len(materials) == 0


@pytest.mark.asyncio
async def test_assign_textbook_to_course(store):
    """Create textbook and course, assign, verify course_id set."""
    course_id = await store.create_course("Assignment Test")
    textbook_id = await store.create_textbook(
        title="Test Book",
        filepath="/path/to/book.pdf"
    )
    
    # Initially course_id should be None
    textbook = await store.get_textbook(textbook_id)
    assert textbook['course_id'] is None
    
    # Assign
    await store.assign_textbook_to_course(textbook_id, course_id)
    
    # Verify
    textbook = await store.get_textbook(textbook_id)
    assert textbook['course_id'] == course_id
    
    # Verify in get_course_textbooks
    textbooks = await store.get_course_textbooks(course_id)
    assert len(textbooks) == 1
    assert textbooks[0]['id'] == textbook_id
