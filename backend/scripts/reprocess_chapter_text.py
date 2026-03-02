"""One-time script: reprocess fragmented extracted_content through the text merge system.

Reads existing DB entries for a chapter, runs _merge_text_by_section() to group
text fragments into coherent section-level blocks, then replaces the old entries.

Figures, tables, and equations are preserved as-is (only text gets merged).

Usage:
    cd backend
    python -m scripts.reprocess_chapter_text
"""

import asyncio
import sys
from pathlib import Path

# Ensure backend/ is on the import path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.pipeline_models import ContentType
from app.services.content_extractor import ContentExtractor
from app.services.storage import MetadataStore

TEXTBOOK_ID = "c60841bd-095d-4f73-a6e3-b48491c129ed"
CHAPTER_ID = "4101789f-511b-4587-8c55-87981195a99d"
CHAPTER_NUMBER = "7"


async def main() -> None:
    store = MetadataStore()
    await store.initialize()
    extractor = ContentExtractor(store)

    # ── 1. Read existing entries ──────────────────────────────────────
    old_entries = await store.get_extracted_content_for_chapter(CHAPTER_ID)
    text_count = sum(1 for e in old_entries if e["content_type"] == "text")
    non_text_count = len(old_entries) - text_count
    print(f"Old entries: {len(old_entries)} total ({text_count} text, {non_text_count} non-text)")

    if not old_entries:
        print("Nothing to reprocess.")
        return

    # ── 2. Convert DB rows → merge-compatible dicts ───────────────────
    # _merge_text_by_section expects {"type": ..., "text": ..., "page_number": ...}
    # Non-text entries pass through the merge unchanged.
    merge_input: list[dict] = []
    for e in old_entries:
        ct = e["content_type"]
        if ct == "text":
            merge_input.append({
                "type": "text",
                "text": e["content"] or "",
                "page_number": e["page_number"],
            })
        else:
            # Figures, tables, equations — carry through unchanged
            merge_input.append({
                "type": ct,  # "figure", "table", "equation"
                "text": e["content"] or "",
                "title": e["title"],
                "page_number": e["page_number"],
                # Preserve existing file_path for figures (images already on disk)
                "_existing_file_path": e.get("file_path"),
            })

    # ── 3. Run the merge ──────────────────────────────────────────────
    merged = await extractor._merge_text_by_section(merge_input, CHAPTER_ID)
    merged_text = sum(1 for e in merged if e.get("type") == "text")
    merged_other = len(merged) - merged_text
    print(f"After merge: {len(merged)} total ({merged_text} text, {merged_other} non-text)")

    # ── 4. Delete old entries from DB ─────────────────────────────────
    deleted = await store.delete_extracted_content_for_chapter(CHAPTER_ID)
    print(f"Deleted {deleted} old rows from DB")

    # ── 5. Delete old .md files from disk (keep images/) ──────────────
    content_dir = Path("data/textbooks") / TEXTBOOK_ID / "chapters" / CHAPTER_NUMBER / "content"
    md_files = list(content_dir.glob("*.md"))
    for f in md_files:
        f.unlink()
    print(f"Deleted {len(md_files)} old .md files from {content_dir}")

    # ── 6. Store merged entries ───────────────────────────────────────
    content_dir.mkdir(parents=True, exist_ok=True)
    stored = 0
    for index, entry in enumerate(merged, start=1):
        entry_type = entry.get("type", "")

        if entry_type == "text":
            content_type = ContentType.text
            title = entry.get("_section_title")
            content = entry.get("text")
        elif entry_type == "figure":
            content_type = ContentType.figure
            title = entry.get("title")
            content = entry.get("text")
        elif entry_type == "table":
            content_type = ContentType.table
            title = entry.get("title")
            content = entry.get("text")
        elif entry_type == "equation":
            content_type = ContentType.equation
            title = entry.get("title")
            content = entry.get("text")
        else:
            continue

        file_path = content_dir / f"{content_type.value}_{index}.md"
        file_path.write_text(content or "", encoding="utf-8")

        await store.create_extracted_content({
            "chapter_id": CHAPTER_ID,
            "content_type": content_type.value,
            "title": title,
            "content": content,
            "file_path": str(file_path),
            "page_number": entry.get("page_number"),
            "order_index": index,
        })
        stored += 1

    print(f"Stored {stored} new entries")

    # ── 7. Verify ─────────────────────────────────────────────────────
    final = await store.get_extracted_content_for_chapter(CHAPTER_ID)
    final_text = sum(1 for e in final if e["content_type"] == "text")
    final_other = len(final) - final_text
    print(f"\nVerification: {len(final)} entries ({final_text} text, {final_other} non-text)")
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
