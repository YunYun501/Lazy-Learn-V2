import json
import logging
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class MinerUExtractor:

    def __init__(self):
        self._do_parse = None
        self._available = False

        try:
            from mineru.cli.common import do_parse
        except ImportError:
            logger.info("MinerU not available; falling back to PyMuPDF text extraction.")
            return

        self._do_parse = do_parse
        self._available = True

    def is_available(self) -> bool:
        return self._available

    def extract_text_by_pages(self, pdf_bytes: bytes, output_dir: str, lang: str = "en") -> dict[int, str]:
        if not self._available or not self._do_parse:
            return {}

        temp_dir = tempfile.mkdtemp(dir=output_dir or None)
        try:
            self._do_parse(
                output_dir=temp_dir,
                pdf_file_names=["document"],
                pdf_bytes_list=[pdf_bytes],
                p_lang_list=[lang],
                backend="pipeline",
                parse_method="auto",
                formula_enable=True,
                table_enable=True,
                f_dump_md=True,
                f_dump_content_list=True,
                f_dump_middle_json=False,
                f_dump_model_output=False,
                f_dump_orig_pdf=False,
                f_draw_layout_bbox=False,
                f_draw_span_bbox=False,
                start_page_id=0,
                end_page_id=None,
            )

            content_list_path = (
                Path(temp_dir)
                / "document"
                / "auto"
                / "document_content_list.json"
            )
            if not content_list_path.exists():
                logger.warning("MinerU content list output missing; falling back to PyMuPDF.")
                return {}

            content_entries = json.loads(content_list_path.read_text(encoding="utf-8"))
            pages: dict[int, list[str]] = {}
            for entry in content_entries:
                entry_type = entry.get("type")
                if entry_type == "discarded":
                    continue
                text = entry.get("text")
                if not text:
                    continue
                page_idx = entry.get("page_idx")
                if page_idx is None:
                    continue
                page_number = int(page_idx) + 1
                pages.setdefault(page_number, []).append(text)

            return {page: "\n".join(texts) for page, texts in pages.items()}
        except Exception as e:
            logger.warning(f"MinerU extraction failed; falling back to PyMuPDF: {e}")
            return {}
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
