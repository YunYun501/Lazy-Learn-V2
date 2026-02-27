import pytest
import tempfile
from pathlib import Path
from app.services.storage import MetadataStore
from app.services.filesystem import FilesystemManager

@pytest.fixture
async def store(tmp_path):
    """Create a MetadataStore with a temporary database."""
    db_path = tmp_path / "test.db"
    store = MetadataStore(db_path=db_path)
    await store.initialize()
    return store

@pytest.fixture
def fs(tmp_path):
    """Create a FilesystemManager with a temporary data directory."""
    manager = FilesystemManager(data_dir=tmp_path / "data")
    manager.initialize()
    return manager

@pytest.mark.asyncio
async def test_textbook_crud(store):
    """Test creating and retrieving a textbook record."""
    # Create
    textbook_id = await store.create_textbook(
        title="Digital Control Systems",
        filepath="/path/to/textbook.pdf",
        course="MECH0089",
        library_type="course",
    )
    assert textbook_id is not None

    # Retrieve
    textbook = await store.get_textbook(textbook_id)
    assert textbook is not None
    assert textbook["title"] == "Digital Control Systems"
    assert textbook["course"] == "MECH0089"
    assert textbook["library_type"] == "course"
    assert textbook["processed_at"] is None

    # List by course
    textbooks = await store.list_textbooks(course="MECH0089")
    assert len(textbooks) == 1
    assert textbooks[0]["id"] == textbook_id

    # Mark processed
    await store.mark_textbook_processed(textbook_id)
    textbook = await store.get_textbook(textbook_id)
    assert textbook["processed_at"] is not None

@pytest.mark.asyncio
async def test_chapter_crud(store):
    """Test creating and listing chapters."""
    textbook_id = await store.create_textbook("Test Book", "/path/test.pdf")
    chapter_id = await store.create_chapter(
        textbook_id=textbook_id,
        chapter_number="3",
        title="The Z-Transform",
        page_start=44,
        page_end=103,
    )
    assert chapter_id is not None

    chapters = await store.list_chapters(textbook_id)
    assert len(chapters) == 1
    assert chapters[0]["title"] == "The Z-Transform"
    assert chapters[0]["page_start"] == 44

def test_filesystem_layout_creation(fs):
    """Test that filesystem directories are created correctly."""
    textbook_id = "test-textbook-123"
    dirs = fs.setup_textbook_dirs(textbook_id)

    assert dirs["base"].exists()
    assert dirs["images"].exists()
    assert dirs["chapters"].exists()

    # Verify path helpers
    chapter_path = fs.chapter_text_path(textbook_id, "3")
    assert str(chapter_path).endswith("3.txt")

    img_path = fs.image_path(textbook_id, 45, 0)
    assert str(img_path).endswith("page45_img0.png")

    desc_path = fs.description_path(textbook_id, "3")
    assert str(desc_path).endswith("chapter_3.md")
    assert desc_path.parent.exists()
