from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
import io


class SectionContent:
    def __init__(self, section: str, text: str, heading_level: int = 0, image_paths: list[str] = None):
        self.section = section
        self.text = text
        self.heading_level = heading_level
        self.image_paths = image_paths or []


class DOCXParser:
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir

    def parse(self, filepath: str) -> list[SectionContent]:
        """Parse a DOCX file. Returns list of SectionContent with heading detection."""
        doc = Document(filepath)
        sections = []
        current_section = "Introduction"
        current_heading_level = 0
        current_text_parts = []
        image_paths = []

        for para in doc.paragraphs:
            style_name = para.style.name if para.style else ""

            # Detect headings
            if style_name.startswith("Heading"):
                # Save previous section
                if current_text_parts:
                    sections.append(SectionContent(
                        section=current_section,
                        text="\n".join(current_text_parts),
                        heading_level=current_heading_level,
                        image_paths=image_paths,
                    ))
                    image_paths = []
                    current_text_parts = []

                # Start new section
                current_section = para.text.strip() or current_section
                try:
                    current_heading_level = int(style_name.replace("Heading ", ""))
                except ValueError:
                    current_heading_level = 1
            else:
                if para.text.strip():
                    current_text_parts.append(para.text.strip())

        # Save last section
        if current_text_parts:
            sections.append(SectionContent(
                section=current_section,
                text="\n".join(current_text_parts),
                heading_level=current_heading_level,
                image_paths=image_paths,
            ))

        # Extract images from document
        if self.output_dir:
            for rel in doc.part.rels.values():
                if "image" in rel.reltype:
                    try:
                        img_data = rel.target_part.blob
                        ext = rel.target_part.content_type.split("/")[-1]
                        img_path = self.output_dir / f"doc_img_{len(image_paths)}.{ext}"
                        img_path.write_bytes(img_data)
                        if sections:
                            sections[-1].image_paths.append(str(img_path))
                    except Exception:
                        pass

        return sections

    def to_chapters(self, sections: list[SectionContent]) -> list[dict]:
        """Convert sections to chapter-like structure for unified processing."""
        return [
            {
                "number": str(i + 1),
                "title": s.section,
                "text": s.text,
                "page_start": i + 1,
                "page_end": i + 1,
                "heading_level": s.heading_level,
                "image_paths": s.image_paths,
            }
            for i, s in enumerate(sections)
        ]
