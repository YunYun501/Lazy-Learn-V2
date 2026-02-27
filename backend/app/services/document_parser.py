from pathlib import Path
from app.services.pptx_parser import PPTXParser
from app.services.docx_parser import DOCXParser


class ParsedDocument:
    """Unified document representation regardless of source format."""
    def __init__(self, filepath: str, file_type: str, chapters: list[dict]):
        self.filepath = filepath
        self.file_type = file_type  # "pdf", "pptx", "docx"
        self.chapters = chapters
        self.total_pages = len(chapters)


class DocumentParser:
    """Unified dispatcher that routes to the appropriate parser by file type."""

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir

    def parse(self, filepath: str) -> ParsedDocument:
        """Parse any supported document type. Returns unified ParsedDocument."""
        path = Path(filepath)
        ext = path.suffix.lower()

        if ext == ".pptx":
            parser = PPTXParser(output_dir=self.output_dir)
            slides = parser.parse(filepath)
            chapters = parser.to_chapters(slides)
            return ParsedDocument(filepath, "pptx", chapters)

        elif ext == ".docx":
            parser = DOCXParser(output_dir=self.output_dir)
            sections = parser.parse(filepath)
            chapters = parser.to_chapters(sections)
            return ParsedDocument(filepath, "docx", chapters)

        elif ext == ".pdf":
            raise ValueError("Use PDFParser for PDF files (requires async + storage)")

        else:
            raise ValueError(f"Unsupported file type: {ext}. Supported: .pptx, .docx")
