import re
from pathlib import Path
from app.models.description_schema import ChapterDescription, ConceptEntry


def serialize_to_md(desc: ChapterDescription) -> str:
    """Serialize a ChapterDescription to a keyword-searchable .md string."""
    lines = []
    lines.append(f"# {desc.chapter_title}")
    lines.append(f"")
    lines.append(f"**Source**: {desc.source_textbook}")
    lines.append(f"**Chapter**: {desc.chapter_number}")
    lines.append(f"**Pages**: {desc.page_range[0]}-{desc.page_range[1]}")
    lines.append(f"")
    lines.append(f"## Summary")
    lines.append(f"")
    lines.append(desc.summary)
    lines.append(f"")
    lines.append(f"## Key Concepts")
    lines.append(f"")
    for concept in desc.key_concepts:
        # Format: [EXPLAINS] Z-transform (aliases: z transform, ZT)
        aliases_str = f" (aliases: {', '.join(concept.aliases)})" if concept.aliases else ""
        lines.append(f"- [{concept.classification}] {concept.name}{aliases_str}")
        lines.append(f"  {concept.description}")
    lines.append(f"")
    lines.append(f"## Prerequisites")
    lines.append(f"")
    for prereq in desc.prerequisites:
        lines.append(f"- {prereq}")
    lines.append(f"")
    lines.append(f"## Mathematical Content")
    lines.append(f"")
    for eq in desc.mathematical_content:
        lines.append(f"- {eq}")
    lines.append(f"")
    lines.append(f"## Figures")
    lines.append(f"")
    lines.append(f"**Has Figures**: {'Yes' if desc.has_figures else 'No'}")
    for fig in desc.figure_descriptions:
        lines.append(f"- {fig}")
    lines.append(f"")
    return "\n".join(lines)


def parse_from_md(md_text: str, source_textbook: str = "") -> ChapterDescription:
    """Parse a .md description back to a ChapterDescription object."""
    lines = md_text.strip().split("\n")

    # Extract title from first # heading
    chapter_title = ""
    chapter_number = ""
    page_range = (0, 0)
    summary_lines = []
    key_concepts = []
    prerequisites = []
    mathematical_content = []
    has_figures = False
    figure_descriptions = []

    section = None
    for line in lines:
        line = line.rstrip()
        if line.startswith("# "):
            chapter_title = line[2:].strip()
        elif line.startswith("**Source**:"):
            source_textbook = line.split(":", 1)[1].strip()
        elif line.startswith("**Chapter**:"):
            chapter_number = line.split(":", 1)[1].strip()
        elif line.startswith("**Pages**:"):
            pages_str = line.split(":", 1)[1].strip()
            parts = pages_str.split("-")
            if len(parts) == 2:
                page_range = (int(parts[0].strip()), int(parts[1].strip()))
        elif line.startswith("## Summary"):
            section = "summary"
        elif line.startswith("## Key Concepts"):
            section = "concepts"
        elif line.startswith("## Prerequisites"):
            section = "prerequisites"
        elif line.startswith("## Mathematical Content"):
            section = "math"
        elif line.startswith("## Figures"):
            section = "figures"
        elif line.startswith("**Has Figures**:"):
            has_figures = "Yes" in line
        elif section == "summary" and line and not line.startswith("#"):
            summary_lines.append(line)
        elif section == "concepts" and line.startswith("- ["):
            # Parse: - [EXPLAINS] Z-transform (aliases: z transform, ZT)
            match = re.match(r"- \[(EXPLAINS|USES)\] (.+?)(?:\s+\(aliases: (.+?)\))?$", line)
            if match:
                classification = match.group(1)
                name = match.group(2).strip()
                aliases = [a.strip() for a in match.group(3).split(",")] if match.group(3) else []
                key_concepts.append(ConceptEntry(
                    name=name,
                    aliases=aliases,
                    classification=classification,
                    description="",  # Description is on next line
                ))
        elif section == "concepts" and line.startswith("  ") and key_concepts:
            # Description line for last concept
            key_concepts[-1] = key_concepts[-1].model_copy(
                update={"description": line.strip()}
            )
        elif section == "prerequisites" and line.startswith("- "):
            prerequisites.append(line[2:].strip())
        elif section == "math" and line.startswith("- "):
            mathematical_content.append(line[2:].strip())
        elif section == "figures" and line.startswith("- "):
            figure_descriptions.append(line[2:].strip())

    return ChapterDescription(
        source_textbook=source_textbook,
        chapter_number=chapter_number,
        chapter_title=chapter_title,
        page_range=page_range,
        summary=" ".join(summary_lines).strip(),
        key_concepts=key_concepts,
        prerequisites=prerequisites,
        mathematical_content=mathematical_content,
        has_figures=has_figures,
        figure_descriptions=figure_descriptions,
    )


def save_description(desc: ChapterDescription, output_dir: Path) -> Path:
    """Save a ChapterDescription as a .md file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"chapter_{desc.chapter_number.replace('.', '_')}.md"
    filepath = output_dir / filename
    filepath.write_text(serialize_to_md(desc), encoding="utf-8")
    return filepath


def load_description(filepath: Path) -> ChapterDescription:
    """Load a ChapterDescription from a .md file."""
    md_text = filepath.read_text(encoding="utf-8")
    return parse_from_md(md_text, source_textbook=filepath.parent.name)


def list_descriptions(descriptions_dir: Path) -> list[Path]:
    """List all .md description files in a directory tree."""
    if not descriptions_dir.exists():
        return []
    return sorted(descriptions_dir.rglob("*.md"))


def search_descriptions(descriptions_dir: Path, keyword: str) -> list[dict]:
    """
    Step 1: Keyword search across all .md descriptions.
    Returns list of {filepath, content, matched_lines} for files containing keyword.
    Case-insensitive search.
    """
    results = []
    keyword_lower = keyword.lower()
    for filepath in list_descriptions(descriptions_dir):
        content = filepath.read_text(encoding="utf-8")
        if keyword_lower in content.lower():
            matched_lines = [
                line for line in content.split("\n")
                if keyword_lower in line.lower()
            ]
            results.append({
                "filepath": str(filepath),
                "content": content,
                "matched_lines": matched_lines,
                "source": filepath.parent.name,
                "chapter": filepath.stem,
            })
    return results
