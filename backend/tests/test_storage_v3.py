import pytest
import tempfile
from pathlib import Path
from app.services.storage import MetadataStore


@pytest.fixture
async def store_v3(tmp_path):
    """Create a MetadataStore with a temporary database for V3 testing."""
    db_path = tmp_path / "test_v3.db"
    store = MetadataStore(db_path=db_path)
    await store.initialize()
    return store


@pytest.mark.asyncio
async def test_concept_nodes_table_created(store_v3):
    """Test that concept_nodes table is created and can store/retrieve nodes."""
    import aiosqlite
    import uuid
    from datetime import datetime

    # Insert a concept node
    node_id = str(uuid.uuid4())
    textbook_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    async with aiosqlite.connect(store_v3.db_path) as db:
        await db.execute(
            """INSERT INTO concept_nodes 
               (id, textbook_id, title, description, node_type, level, 
                source_chapter_id, source_section_id, source_page, metadata_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                node_id,
                textbook_id,
                "Pythagorean Theorem",
                "a² + b² = c²",
                "theorem",
                "chapter",
                None,
                None,
                42,
                '{"proof": "geometric"}',
                now,
            ),
        )
        await db.commit()

        # Retrieve and verify
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM concept_nodes WHERE id = ?", (node_id,)
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None
            assert row["id"] == node_id
            assert row["textbook_id"] == textbook_id
            assert row["title"] == "Pythagorean Theorem"
            assert row["description"] == "a² + b² = c²"
            assert row["node_type"] == "theorem"
            assert row["level"] == "chapter"
            assert row["source_page"] == 42
            assert row["metadata_json"] == '{"proof": "geometric"}'
            assert row["created_at"] == now


@pytest.mark.asyncio
async def test_concept_edges_table_created(store_v3):
    """Test that concept_edges table is created and can store/retrieve edges."""
    import aiosqlite
    import uuid
    from datetime import datetime

    # Insert a concept edge
    edge_id = str(uuid.uuid4())
    textbook_id = str(uuid.uuid4())
    source_node_id = str(uuid.uuid4())
    target_node_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    async with aiosqlite.connect(store_v3.db_path) as db:
        await db.execute(
            """INSERT INTO concept_edges 
               (id, textbook_id, source_node_id, target_node_id, relationship_type, 
                confidence, reasoning, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                edge_id,
                textbook_id,
                source_node_id,
                target_node_id,
                "derives_from",
                0.95,
                "Pythagorean theorem derives from geometry",
                now,
            ),
        )
        await db.commit()

        # Retrieve and verify
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM concept_edges WHERE id = ?", (edge_id,)
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None
            assert row["id"] == edge_id
            assert row["textbook_id"] == textbook_id
            assert row["source_node_id"] == source_node_id
            assert row["target_node_id"] == target_node_id
            assert row["relationship_type"] == "derives_from"
            assert row["confidence"] == 0.95
            assert row["reasoning"] == "Pythagorean theorem derives from geometry"
            assert row["created_at"] == now


@pytest.mark.asyncio
async def test_graph_generation_jobs_table_created(store_v3):
    """Test that graph_generation_jobs table is created and can store/retrieve jobs."""
    import aiosqlite
    import uuid
    from datetime import datetime

    # Insert a graph generation job
    job_id = str(uuid.uuid4())
    textbook_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    async with aiosqlite.connect(store_v3.db_path) as db:
        await db.execute(
            """INSERT INTO graph_generation_jobs 
               (id, textbook_id, status, progress_pct, total_chapters, 
                processed_chapters, error, created_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (job_id, textbook_id, "processing", 50.0, 10, 5, None, now, None),
        )
        await db.commit()

        # Retrieve and verify
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM graph_generation_jobs WHERE id = ?", (job_id,)
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None
            assert row["id"] == job_id
            assert row["textbook_id"] == textbook_id
            assert row["status"] == "processing"
            assert row["progress_pct"] == 50.0
            assert row["total_chapters"] == 10
            assert row["processed_chapters"] == 5
            assert row["error"] is None
            assert row["created_at"] == now
            assert row["completed_at"] is None


@pytest.mark.asyncio
async def test_v3_migration_idempotent(tmp_path):
    """Test that calling initialize() twice on the same DB doesn't error."""
    db_path = tmp_path / "test_idempotent.db"

    # First initialization
    store1 = MetadataStore(db_path=db_path)
    await store1.initialize()

    # Second initialization on same DB
    store2 = MetadataStore(db_path=db_path)
    await store2.initialize()  # Should not raise

    # Verify tables exist
    import aiosqlite

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        # Check concept_nodes table exists
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='concept_nodes'"
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None

        # Check concept_edges table exists
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='concept_edges'"
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None

        # Check graph_generation_jobs table exists
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='graph_generation_jobs'"
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None


@pytest.mark.asyncio
async def test_concept_nodes_indexes_created(store_v3):
    """Test that indexes on concept_nodes are created."""
    import aiosqlite

    async with aiosqlite.connect(store_v3.db_path) as db:
        db.row_factory = aiosqlite.Row

        # Check index exists
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_concept_nodes_textbook'"
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None


@pytest.mark.asyncio
async def test_concept_edges_indexes_created(store_v3):
    """Test that indexes on concept_edges are created."""
    import aiosqlite

    async with aiosqlite.connect(store_v3.db_path) as db:
        db.row_factory = aiosqlite.Row

        # Check index exists
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_concept_edges_textbook'"
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None


@pytest.mark.asyncio
async def test_graph_jobs_indexes_created(store_v3):
    """Test that indexes on graph_generation_jobs are created."""
    import aiosqlite

    async with aiosqlite.connect(store_v3.db_path) as db:
        db.row_factory = aiosqlite.Row

        # Check index exists
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_graph_jobs_textbook'"
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None
