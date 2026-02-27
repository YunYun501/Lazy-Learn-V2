from pydantic import BaseModel
from typing import Literal


class ConceptEntry(BaseModel):
    name: str
    aliases: list[str] = []  # e.g. ["z transform", "ZT", "bilateral Z-transform"]
    classification: Literal["EXPLAINS", "USES"]
    description: str  # Brief description of how this concept appears in the chapter


class ChapterDescription(BaseModel):
    source_textbook: str          # Textbook filename/ID
    chapter_number: str           # e.g. "3" or "3.2"
    chapter_title: str            # e.g. "The Z-Transform"
    page_range: tuple[int, int]   # Start and end pages
    summary: str                  # 2-5 sentence summary
    key_concepts: list[ConceptEntry]  # Each with name, classification, description
    prerequisites: list[str]      # Concepts reader should already know
    mathematical_content: list[str]  # Key equations/theorems described in text
    has_figures: bool             # Whether chapter contains important figures/graphs
    figure_descriptions: list[str]   # Brief description of each key figure
