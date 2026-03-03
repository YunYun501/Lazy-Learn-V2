"""Material Relevance Checker — scores textbook TOC entries against lecture material topics.

Uses a hierarchical funnel approach:
  Pass 1: Score L1 (chapters) → fast, ~13 entries → save + display immediately
  Pass 2: Score L2 (sections) for qualifying L1 parents → save + display
  Pass 3: Score L3 (subsections) for qualifying L2 parents → save + display

Each pass is a small, fast DeepSeek call (3-5s). Results are saved progressively
so the frontend can poll and show partial results while deeper levels are scored.
"""
import json
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from app.services.storage import MetadataStore

logger = logging.getLogger(__name__)

TOP_N_PARENTS = 5
L1_QUALIFY_THRESHOLD = 0.4
L2_QUALIFY_THRESHOLD = 0.4
MAX_CONCURRENT_CALLS = 5

RELEVANCE_CHECK_SYSTEM_PROMPT = (
    "You are a curriculum-mapping assistant. Your job is to score how relevant "
    "each textbook TOC entry is to the provided lecture material topics.\n\n"
    "Scoring target:\n"
    "- For each TOC entry, assign a relevance score in [0.0, 1.0] based on "
    "conceptual overlap with ANY topic (choose the best-matching topic(s)).\n"
    "- Use meaning, not exact wording. Treat common engineering synonyms as "
    "matches (e.g., whirling ≈ rotor whirl; critical speed ≈ resonance speed; "
    "Jeffcott/Laval rotor ≈ rotor model; fatigue ≈ cyclic loading).\n"
    "- Ignore page numbers when judging relevance. Ignore leading database/"
    "index prefixes in titles.\n\n"
    "Score anchors (use these consistently):\n"
    "- 1.0 = direct match to the main subject of a topic (would clearly be "
    "assigned reading for that lecture)\n"
    "- 0.8 = strong overlap (covers key methods/concepts used in the lecture)\n"
    "- 0.5 = partial overlap (some shared concepts, but not the core)\n"
    "- 0.2 = tangential mention/background\n"
    "- 0.0 = unrelated\n\n"
    "Output constraints:\n"
    '- Return ONLY a single JSON object (no markdown, no extra text).\n'
    "- Must include:\n"
    '  - "toc_count": integer N copied from input\n'
    '  - "scores": array of exactly N numbers (floats) where scores[k-1] '
    "corresponds to TOC entry with i=k\n"
    '  - "labels": array of exactly N strings, each one of: '
    '"none","low","med","high"\n'
    '  - "top_matches": array (max 20) of objects with keys: '
    '"i", "score", "topics", "why"\n'
    '- "topics" is an array of topic indices (t values) that justify the score.\n'
    '- "why" is a very short phrase (<= 12 words). Do not include long reasoning.\n'
    "- Do not invent TOC entries or topic indices.\n"
    '- Ensure len(scores)==toc_count and len(labels)==toc_count.'
)


class MaterialRelevanceChecker:
    """Score textbook TOC entries against material topics using a hierarchical funnel."""

    def __init__(self, store: MetadataStore, ai_router: Any) -> None:
        self.store = store
        self.ai_router = ai_router

    async def check(self, material_id: str, course_id: str) -> None:
        """Multi-pass relevance check: L1 → L2 → L3 with progressive saves."""
        try:
            await self.store.update_material_relevance_status(material_id, "checking")

            topics = await self._get_material_topics(material_id)
            if not topics:
                await self.store.save_relevance_results(material_id, [])
                await self.store.update_material_relevance_status(material_id, "completed")
                return

            textbooks = await self.store.get_course_textbooks(course_id)
            if not textbooks:
                await self.store.save_relevance_results(material_id, [])
                await self.store.update_material_relevance_status(material_id, "completed")
                return

            await self.store.delete_relevance_results(material_id)

            for tb in textbooks:
                tb_id = tb["id"]
                all_entries = await self._build_toc_entries(tb_id)
                if not all_entries:
                    continue

                l1 = [e for e in all_entries if e["level"] == 1]
                l2 = [e for e in all_entries if e["level"] == 2]
                l3 = [e for e in all_entries if e["level"] == 3]

                # --- Pass 1: L1 chapters ---
                if l1:
                    self._assign_indices(l1)
                    l1_scores = await self._score_entries(topics, l1)
                    await self._save_level_results(
                        material_id, course_id, tb_id, l1, l1_scores
                    )
                    logger.info(
                        "L1 scored %d chapters for textbook %s", len(l1), tb_id[:8]
                    )

                # --- Pass 2: L2 sections for qualifying L1 parents (parallel by chapter) ---
                qualifying_l1_ids = self._qualifying_parent_ids(
                    l1, l1_scores, TOP_N_PARENTS, L1_QUALIFY_THRESHOLD
                )
                l2_filtered = [e for e in l2 if e["parent_id"] in qualifying_l1_ids]
                all_l2_scores: list[dict] = []

                if l2_filtered:
                    sem = asyncio.Semaphore(MAX_CONCURRENT_CALLS)
                    l2_by_parent: dict[str, list[dict]] = {}
                    for e in l2_filtered:
                        l2_by_parent.setdefault(e["parent_id"], []).append(e)

                    async def _score_l2_group(parent_id: str, group: list[dict]) -> tuple[list[dict], list[dict]]:
                        async with sem:
                            self._assign_indices(group)
                            scores = await self._score_entries(topics, group)
                            await self._save_level_results(
                                material_id, course_id, tb_id, group, scores
                            )
                            return group, scores

                    l2_tasks = [
                        _score_l2_group(pid, grp)
                        for pid, grp in l2_by_parent.items()
                    ]
                    l2_results = await asyncio.gather(*l2_tasks)

                    # Flatten for qualifying parent calculation
                    all_l2_entries: list[dict] = []
                    for grp_entries, grp_scores in l2_results:
                        all_l2_entries.extend(grp_entries)
                        all_l2_scores.extend(grp_scores)

                    logger.info(
                        "L2 scored %d sections (from %d qualifying chapters, %d parallel calls)",
                        len(l2_filtered), len(qualifying_l1_ids), len(l2_by_parent),
                    )
                else:
                    all_l2_entries = []

                # --- Pass 3: L3 subsections for qualifying L2 parents (parallel by section) ---
                qualifying_l2_ids = self._qualifying_parent_ids(
                    all_l2_entries if l2_filtered else [],
                    all_l2_scores,
                    TOP_N_PARENTS, L2_QUALIFY_THRESHOLD,
                )
                l3_filtered = [e for e in l3 if e["parent_id"] in qualifying_l2_ids]

                if l3_filtered:
                    sem = asyncio.Semaphore(MAX_CONCURRENT_CALLS)
                    l3_by_parent: dict[str, list[dict]] = {}
                    for e in l3_filtered:
                        l3_by_parent.setdefault(e["parent_id"], []).append(e)

                    async def _score_l3_group(parent_id: str, group: list[dict]) -> tuple[list[dict], list[dict]]:
                        async with sem:
                            self._assign_indices(group)
                            scores = await self._score_entries(topics, group)
                            await self._save_level_results(
                                material_id, course_id, tb_id, group, scores
                            )
                            return group, scores

                    l3_tasks = [
                        _score_l3_group(pid, grp)
                        for pid, grp in l3_by_parent.items()
                    ]
                    l3_results = await asyncio.gather(*l3_tasks)

                    total_l3 = sum(len(grp) for grp, _ in l3_results)
                    logger.info(
                        "L3 scored %d subsections (from %d qualifying sections, %d parallel calls)",
                        total_l3, len(qualifying_l2_ids), len(l3_by_parent),
                    )

            await self.store.update_material_relevance_status(material_id, "completed")

        except Exception:
            logger.exception("Relevance check failed for material %s", material_id)
            await self.store.update_material_relevance_status(material_id, "error")
            raise

    # ------------------------------------------------------------------ #
    # Helpers                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _assign_indices(entries: list[dict]) -> None:
        for i, entry in enumerate(entries, start=1):
            entry["i"] = i

    @staticmethod
    def _qualifying_parent_ids(
        entries: list[dict],
        scores: list[dict],
        top_n: int,
        threshold: float,
    ) -> set[str]:
        if not entries or not scores:
            return set()

        scored_pairs = []
        for idx, entry in enumerate(entries):
            s = scores[idx].get("score", 0.0) if idx < len(scores) else 0.0
            scored_pairs.append((entry["id"], s))

        above_threshold = {eid for eid, s in scored_pairs if s >= threshold}
        by_score = sorted(scored_pairs, key=lambda x: -x[1])
        top_ids = {eid for eid, _ in by_score[:top_n]}

        return above_threshold | top_ids

    async def _save_level_results(
        self,
        material_id: str,
        course_id: str,
        textbook_id: str,
        entries: list[dict],
        scores: list[dict],
    ) -> None:
        now = datetime.utcnow().isoformat()
        rows: list[dict] = []

        for idx, entry in enumerate(entries):
            hit = scores[idx] if idx < len(scores) else {}
            score = max(0.0, min(1.0, float(hit.get("score", 0.0))))
            matched = hit.get("matched_topics", [])
            reasoning = hit.get("reasoning", "")

            rows.append({
                "id": str(uuid.uuid4()),
                "material_id": material_id,
                "course_id": course_id,
                "textbook_id": textbook_id,
                "entry_id": entry["id"],
                "entry_type": entry["type"],
                "entry_title": entry["title"],
                "entry_level": entry["level"],
                "page_start": entry.get("page_start"),
                "page_end": entry.get("page_end"),
                "relevance_score": score,
                "matched_topics": json.dumps(matched) if matched else None,
                "reasoning": reasoning or None,
                "parent_entry_id": entry.get("parent_id"),
                "created_at": now,
            })

        await self.store.append_relevance_results(rows)

    async def _get_material_topics(self, material_id: str) -> list[dict]:
        summary = await self.store.get_material_summary(material_id)
        if not summary:
            return []

        raw_json = summary.get("summary_json")
        if not raw_json:
            return []

        try:
            data: dict = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
            topics: list[dict] = []
            for idx, topic in enumerate(data.get("topics", []), start=1):
                title: str = topic.get("title", "")
                desc: str = topic.get("description", "")
                if title:
                    topics.append({"t": idx, "title": title, "desc": desc})
            return topics
        except (json.JSONDecodeError, AttributeError, TypeError):
            return []

    @staticmethod
    def _clean_title(raw_title: str) -> str:
        return raw_title.strip()

    async def _build_toc_entries(self, textbook_id: str) -> list[dict]:
        """Build flat list of all TOC entries with path strings. Indices assigned per-level later."""
        entries: list[dict] = []
        chapters = await self.store.list_chapters(textbook_id)

        for ch in chapters:
            ch_id = ch["id"]
            ch_title = self._clean_title(ch.get("title", ""))
            ch_path = ch_title

            entries.append({
                "id": ch_id,
                "type": "chapter",
                "title": ch_title,
                "level": 1,
                "page_start": ch.get("page_start"),
                "page_end": ch.get("page_end"),
                "parent_id": None,
                "path": ch_path,
            })

            sections = await self.store.get_sections_for_chapter(ch_id)
            for sec in sections:
                sec_id = sec["id"]
                sec_title = self._clean_title(
                    sec.get("title") or f"Section {sec.get('section_number', '?')}"
                )
                sec_path = f"{ch_path} > {sec_title}"

                entries.append({
                    "id": sec_id,
                    "type": "section",
                    "title": sec_title,
                    "level": 2,
                    "page_start": sec.get("page_start"),
                    "page_end": sec.get("page_end"),
                    "parent_id": ch_id,
                    "path": sec_path,
                })

                subsections = await self.store.get_subsections_for_section(sec_id)
                for sub in subsections:
                    sub_title = self._clean_title(
                        sub.get("title") or f"Subsection {sub.get('section_number', '?')}"
                    )
                    entries.append({
                        "id": sub["id"],
                        "type": "subsection",
                        "title": sub_title,
                        "level": 3,
                        "page_start": sub.get("page_start"),
                        "page_end": sub.get("page_end"),
                        "parent_id": sec_id,
                        "path": f"{sec_path} > {sub_title}",
                    })

        return entries

    async def _score_entries(
        self, topics: list[dict], entries: list[dict]
    ) -> list[dict]:
        """Score entries via DeepSeek. Returns positional list of {score, label, matched_topics, reasoning}."""
        n = len(entries)
        empty_result: list[dict] = [{}] * n

        topics_json = json.dumps(
            [{"t": t["t"], "title": t["title"], "desc": t["desc"]} for t in topics],
            ensure_ascii=False,
        )

        toc_json = json.dumps(
            [{"i": e["i"], "lvl": e["level"], "path": e["path"], "title": e["title"]}
             for e in entries],
            ensure_ascii=False,
        )

        user_content = (
            "INPUT\n"
            f"topics:\n{topics_json}\n\n"
            f"toc_count: {n}\n\n"
            f"toc_entries:\n{toc_json}\n\n"
            "TASK\n"
            "Compute relevance for every TOC entry. Produce JSON exactly following "
            "the required output keys and sizes.\n"
            "Remember: scores array index = i-1 (positional). "
            f"Ensure len(scores)=={n} and len(labels)=={n}."
        )

        messages = [
            {"role": "system", "content": RELEVANCE_CHECK_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        for attempt in range(2):
            try:
                response: dict = await self.ai_router.get_json_response(
                    messages, temperature=0.0, timeout=60.0
                )

                scores = response.get("scores", [])
                labels = response.get("labels", [])
                top_matches = response.get("top_matches", [])

                if len(scores) != n:
                    logger.warning(
                        "Scores length mismatch: expected %d, got %d (attempt %d)",
                        n, len(scores), attempt + 1,
                    )
                    if attempt == 0:
                        messages.append({
                            "role": "user",
                            "content": (
                                f"ERROR: You returned {len(scores)} scores but "
                                f"toc_count is {n}. Return exactly {n} scores and "
                                f"{n} labels. Try again."
                            ),
                        })
                        continue
                    scores = (scores + [0.0] * n)[:n]
                    labels = (labels + ["none"] * n)[:n]

                top_lookup: dict[int, dict] = {}
                for tm in top_matches:
                    if isinstance(tm, dict) and "i" in tm:
                        top_lookup[tm["i"]] = tm

                result: list[dict] = []
                for idx in range(n):
                    entry_i = idx + 1
                    score_val = scores[idx] if idx < len(scores) else 0.0
                    label_val = labels[idx] if idx < len(labels) else "none"

                    tm_info = top_lookup.get(entry_i, {})
                    topic_indices = tm_info.get("topics", [])
                    matched_names = []
                    for ti in topic_indices:
                        for t in topics:
                            if t["t"] == ti:
                                matched_names.append(t["title"])
                                break

                    result.append({
                        "score": float(score_val),
                        "label": label_val,
                        "matched_topics": matched_names,
                        "reasoning": tm_info.get("why", ""),
                    })

                logger.info(
                    "Scored %d entries: %d high, %d med, %d low",
                    n,
                    sum(1 for r in result if r["score"] > 0.7),
                    sum(1 for r in result if 0.4 <= r["score"] <= 0.7),
                    sum(1 for r in result if 0.0 < r["score"] < 0.4),
                )
                return result

            except Exception:
                logger.exception("AI scoring failed (attempt %d)", attempt + 1)
                if attempt == 0:
                    continue
                return empty_result

        return empty_result
