from pathlib import Path
import shutil

class FilesystemManager:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.textbooks_dir = data_dir / "textbooks"
        self.descriptions_dir = data_dir / "descriptions"

    def initialize(self):
        """Create base directory structure."""
        self.textbooks_dir.mkdir(parents=True, exist_ok=True)
        self.descriptions_dir.mkdir(parents=True, exist_ok=True)
        (self.descriptions_dir / "math_library").mkdir(exist_ok=True)

    def textbook_dir(self, textbook_id: str) -> Path:
        """Get the directory for a specific textbook."""
        return self.textbooks_dir / textbook_id

    def setup_textbook_dirs(self, textbook_id: str) -> dict[str, Path]:
        """Create directory structure for a new textbook. Returns dict of paths."""
        base = self.textbook_dir(textbook_id)
        dirs = {
            "base": base,
            "images": base / "images",
            "chapters": base / "chapters",
        }
        for d in dirs.values():
            d.mkdir(parents=True, exist_ok=True)
        return dirs

    def chapter_text_path(self, textbook_id: str, chapter_num: str) -> Path:
        """Path for extracted chapter text."""
        return self.textbooks_dir / textbook_id / "chapters" / f"{chapter_num}.txt"

    def image_path(self, textbook_id: str, page: int, img_index: int) -> Path:
        """Path for an extracted image."""
        return self.textbooks_dir / textbook_id / "images" / f"page{page}_img{img_index}.png"

    def description_path(self, textbook_id: str, chapter_num: str) -> Path:
        """Path for a generated chapter description."""
        desc_dir = self.descriptions_dir / textbook_id
        desc_dir.mkdir(parents=True, exist_ok=True)
        return desc_dir / f"chapter_{chapter_num.replace('.', '_')}.md"

    def course_descriptions_dir(self, course_name: str) -> Path:
        """Directory for course-specific descriptions."""
        d = self.descriptions_dir / course_name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def math_library_dir(self) -> Path:
        """Directory for math library descriptions (always available)."""
        return self.descriptions_dir / "math_library"

    def save_original_pdf(self, textbook_id: str, source_path: Path) -> Path:
        """Copy original PDF to the textbook directory."""
        dest = self.textbook_dir(textbook_id) / "original.pdf"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest)
        return dest
