import json
import pytest
import aiosqlite

from app.services.storage import MetadataStore


@pytest.fixture
async def store(tmp_path):
    """Create a test MetadataStore with initialized DB."""
    db_path = tmp_path / "test.db"
    store = MetadataStore(db_path=db_path)
    await store.initialize()
    return store


async def _seed_textbook_and_node(store):
    """Helper to create a textbook and concept node for testing."""
    textbook_id = await store.create_textbook("Test Book", "/path/test.pdf")
    node_id = await store.create_concept_node(
        textbook_id=textbook_id,
        title="Test Node",
        node_type="concept",
        level="1",
        description="A test concept node",
        metadata_json=json.dumps({"key": "original_value"}),
    )
    return textbook_id, node_id


@pytest.mark.asyncio
async def test_update_existing_node_metadata(store):
    """Test updating metadata on an existing node."""
    textbook_id, node_id = await _seed_textbook_and_node(store)

    new_metadata = json.dumps({"key": "updated_value", "extra": "data"})
    await store.update_concept_node_metadata(node_id, new_metadata)

    async with aiosqlite.connect(store.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT metadata_json FROM concept_nodes WHERE id = ?", (node_id,)
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None
            assert row["metadata_json"] == new_metadata


@pytest.mark.asyncio
async def test_update_nonexistent_node_is_silent(store):
    """Test that updating a non-existent node does not raise an error."""
    fake_node_id = "nonexistent-node-id"
    new_metadata = json.dumps({"key": "value"})

    await store.update_concept_node_metadata(fake_node_id, new_metadata)


@pytest.mark.asyncio
async def test_update_preserves_other_columns(store):
    """Test that updating metadata does not affect other columns."""
    textbook_id, node_id = await _seed_textbook_and_node(store)

    async with aiosqlite.connect(store.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT title, node_type, description FROM concept_nodes WHERE id = ?",
            (node_id,),
        ) as cursor:
            original = dict(await cursor.fetchone())

    new_metadata = json.dumps({"completely": "different"})
    await store.update_concept_node_metadata(node_id, new_metadata)

    async with aiosqlite.connect(store.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT title, node_type, description FROM concept_nodes WHERE id = ?",
            (node_id,),
        ) as cursor:
            updated = dict(await cursor.fetchone())

    assert updated["title"] == original["title"]
    assert updated["node_type"] == original["node_type"]
    assert updated["description"] == original["description"]


@pytest.mark.asyncio
async def test_update_with_complex_nested_json(store):
    """Test updating with complex nested JSON including arrays."""
    textbook_id, node_id = await _seed_textbook_and_node(store)

    complex_metadata = json.dumps(
        {
            "equation_components": [
                {"type": "variable", "name": "x"},
                {"type": "operator", "name": "+"},
                {"type": "variable", "name": "y"},
            ],
            "defining_equation": "x + y = z",
            "properties": {
                "commutative": True,
                "associative": True,
            },
        }
    )

    await store.update_concept_node_metadata(node_id, complex_metadata)

    async with aiosqlite.connect(store.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT metadata_json FROM concept_nodes WHERE id = ?", (node_id,)
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None
            stored_metadata = json.loads(row["metadata_json"])
            assert len(stored_metadata["equation_components"]) == 3
            assert stored_metadata["defining_equation"] == "x + y = z"
            assert stored_metadata["properties"]["commutative"] is True
