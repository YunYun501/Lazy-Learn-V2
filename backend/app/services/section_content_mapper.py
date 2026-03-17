"""Maps extracted_content entries to sections using page number ranges."""

import aiosqlite
from app.services.storage import MetadataStore


async def map_content_to_sections(
    store: MetadataStore, chapter_id: str
) -> dict[str, list[dict]]:
    """Map extracted_content entries to sections via page_number matching.

    Returns {section_id: [content_entry_dicts]}.

    Assignment rules:
    - Content with page_number between section.page_start and section.page_end → assigned there.
    - Content with no page_number → assign to first section (lowest page_start).
    - Content outside all sections → assign to nearest section by page distance
      (min abs(page_number - page_start)).
    """
    async with aiosqlite.connect(store.db_path) as db:
        db.row_factory = aiosqlite.Row

        # Fetch all sections ordered by page_start
        async with db.execute(
            "SELECT * FROM sections WHERE chapter_id = ? ORDER BY page_start",
            (chapter_id,),
        ) as cursor:
            sections = [dict(row) async for row in cursor]

        # Fetch all extracted_content ordered by page_number, order_index
        async with db.execute(
            "SELECT * FROM extracted_content WHERE chapter_id = ? ORDER BY page_number, order_index",
            (chapter_id,),
        ) as cursor:
            content_entries = [dict(row) async for row in cursor]

    if not sections or not content_entries:
        return {}

    # Build result dict keyed by section_id
    result: dict[str, list[dict]] = {}

    # First section (lowest page_start) for null page_number fallback
    first_section = sections[0]

    for entry in content_entries:
        page_num = entry.get("page_number")

        if page_num is None:
            # Assign to first section
            target_id = first_section["id"]
        else:
            # Try to find a section that contains this page
            matched_id = None
            for sec in sections:
                ps = sec.get("page_start")
                pe = sec.get("page_end")
                if ps is not None and pe is not None and ps <= page_num <= pe:
                    matched_id = sec["id"]
                    break

            if matched_id is not None:
                target_id = matched_id
            else:
                # Orphan: find nearest section by distance to page_start
                def _distance(sec: dict) -> int:
                    ps = sec.get("page_start")
                    if ps is None:
                        return 10**9
                    return abs(page_num - ps)

                nearest = min(sections, key=_distance)
                target_id = nearest["id"]

        result.setdefault(target_id, []).append(entry)

    return result


async def compute_section_path(
    store: MetadataStore, section_id: str, chapter_number: str
) -> str:
    """Walk parent_section_id chain to build hierarchical path.

    Root section (no parent): "CH{chapter_number}/{section_number}"
    Child section: "CH{chapter_number}/{parent_section_number}/{section_number}"
    """
    async with aiosqlite.connect(store.db_path) as db:
        db.row_factory = aiosqlite.Row

        # Collect the chain from this section up to root
        chain: list[dict] = []
        current_id: str | None = section_id

        while current_id is not None:
            async with db.execute(
                "SELECT * FROM sections WHERE id = ?", (current_id,)
            ) as cursor:
                row = await cursor.fetchone()

            if row is None:
                break

            sec = dict(row)
            chain.append(sec)
            parent_id = sec.get("parent_section_id")
            # Treat empty string as None (SQLite may store empty string)
            current_id = parent_id if parent_id else None

    # chain[0] = target section, chain[-1] = root
    # Reverse to get root → ... → target
    chain.reverse()

    parts = [f"CH{chapter_number}"] + [str(sec["section_number"]) for sec in chain]
    return "/".join(parts)


async def get_sections_with_content(
    store: MetadataStore, chapter_id: str
) -> list[dict]:
    """Returns sections that have at least one extracted_content entry mapped.

    Each dict has: section fields + 'content_entries' list + 'section_path' string.

    When a chapter has no sections but does have extracted content, a synthetic
    section covering the full chapter is returned so content is not orphaned
    and the knowledge graph builder can still run concept extraction.
    """
    # Get the full chapter row for metadata and chapter_number
    async with aiosqlite.connect(store.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM chapters WHERE id = ?", (chapter_id,)
        ) as cursor:
            ch_row = await cursor.fetchone()

    if not ch_row:
        return []

    chapter = dict(ch_row)
    chapter_number = chapter["chapter_number"]

    # Map content to sections
    mapping = await map_content_to_sections(store, chapter_id)

    if not mapping:
        # Fallback: chapter has no sections — check for orphaned content
        async with aiosqlite.connect(store.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM extracted_content WHERE chapter_id = ? "
                "ORDER BY page_number, order_index",
                (chapter_id,),
            ) as cursor:
                content_entries = [dict(row) async for row in cursor]

        if not content_entries:
            return []

        # Build a synthetic section from the chapter itself so the graph
        # builder can still run LLM concept extraction on the content.
        return [
            {
                "id": chapter_id,
                "chapter_id": chapter_id,
                "section_number": 1,
                "title": chapter.get("title", ""),
                "page_start": chapter.get("page_start"),
                "page_end": chapter.get("page_end"),
                "parent_section_id": None,
                "level": 1,
                "content_entries": content_entries,
                "section_path": f"CH{chapter_number}",
            }
        ]

    # Fetch section details for each section that has content
    result: list[dict] = []
    async with aiosqlite.connect(store.db_path) as db:
        db.row_factory = aiosqlite.Row
        for section_id, entries in mapping.items():
            async with db.execute(
                "SELECT * FROM sections WHERE id = ?", (section_id,)
            ) as cursor:
                sec_row = await cursor.fetchone()

            if sec_row is None:
                continue

            sec_dict = dict(sec_row)
            sec_dict["content_entries"] = entries
            sec_dict["section_path"] = await compute_section_path(
                store, section_id, chapter_number
            )
            result.append(sec_dict)

    return result
