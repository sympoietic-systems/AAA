import logging
import re
from abc import ABC, abstractmethod
from html.parser import HTMLParser
from pathlib import Path

from backend.utils.token_counter import estimate_tokens

logger = logging.getLogger(__name__)

# pdfminer (under pdfplumber) emits noisy WARNING lines when a font descriptor
# lacks a parseable FontBBox; it falls back to defaults and extraction is
# unaffected. Silence these to keep logs readable.
logging.getLogger("pdfminer.pdffont").setLevel(logging.ERROR)
logging.getLogger("pdfminer.pdfinterp").setLevel(logging.ERROR)

TEXT_EXTENSIONS = {".txt", ".md", ".py", ".json", ".yaml", ".yml", ".csv", ".xml", ".html", ".css", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go", ".java", ".c", ".h", ".cpp", ".hpp", ".sh", ".bat", ".ps1", ".toml", ".ini", ".cfg", ".env", ".log"}


class FileDigester(ABC):
    @abstractmethod
    def extract(self, file_path: Path, file_type: str) -> str: ...

    @abstractmethod
    def chunk(self, text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]: ...


class SimpleChunkDigester(FileDigester):
    def extract(self, file_path: Path, file_type: str) -> str:
        ext = file_path.suffix.lower()

        if ext == ".pdf":
            return self._extract_pdf(file_path)
        if ext == ".docx":
            return self._extract_docx(file_path)
        if ext == ".epub":
            return self._extract_epub(file_path)
        if ext == ".mobi":
            return self._extract_mobi(file_path)
        if ext in TEXT_EXTENSIONS:
            return self._extract_text(file_path)

        raise ValueError(f"Unsupported file type: {ext}")

    def chunk(self, text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
        if not text.strip():
            return []

        words = text.split()
        if not words:
            return []

        chunks: list[str] = []
        step = max(1, chunk_size - overlap)
        i = 0

        while i < len(words):
            chunk_words = words[i:i + chunk_size]
            chunks.append(" ".join(chunk_words))
            i += step

        return chunks

    @staticmethod
    def _extract_text(file_path: Path) -> str:
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return file_path.read_text(encoding="latin-1")

    @staticmethod
    def _extract_pdf(file_path: Path) -> str:
        try:
            import pdfplumber
        except ImportError:
            raise ImportError(
                "pdfplumber is required for PDF extraction. Install with: pip install pdfplumber"
            )

        try:
            return PDFHeadingExtractor.extract(file_path, pdfplumber)
        except Exception as e:
            logger.warning("PDF font-aware heading extraction failed (%s); falling back to plain text", e)
            text_parts: list[str] = []
            with pdfplumber.open(str(file_path)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n\n".join(text_parts)

    @staticmethod
    def _extract_docx(file_path: Path) -> str:
        try:
            from docx import Document
        except ImportError:
            raise ImportError(
                "python-docx is required for DOCX extraction. Install with: pip install python-docx"
            )

        doc = Document(str(file_path))
        parts: list[str] = []
        for p in doc.paragraphs:
            if not p.text.strip():
                continue
            style_name = (p.style.name if p.style else "") or ""
            m = re.match(r'^Heading\s+(\d+)$', style_name)
            if m:
                level = min(int(m.group(1)), 6)
                parts.append("#" * level + " " + p.text.strip())
            else:
                parts.append(p.text)
        return "\n\n".join(parts)

    @staticmethod
    def _extract_epub(file_path: Path) -> str:
        try:
            import ebooklib
            from ebooklib import epub
        except ImportError:
            raise ImportError(
                "ebooklib is required for EPUB extraction. Install with: pip install EbookLib"
            )

        book = epub.read_epub(str(file_path))
        text_parts = []
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                content_bytes = item.get_content()
                try:
                    content_str = content_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    content_str = content_bytes.decode("latin-1", errors="ignore")
                
                parser = EPUBMOBIHTMLParser()
                parser.feed(content_str)
                cleaned_text = parser.get_text()
                if cleaned_text.strip():
                    text_parts.append(cleaned_text.strip())

        if not text_parts:
            raise ValueError("No text content could be extracted from the EPUB file.")

        return "\n\n".join(text_parts)

    @staticmethod
    def _extract_mobi(file_path: Path) -> str:
        try:
            import mobi
        except ImportError:
            raise ImportError(
                "mobi is required for MOBI extraction. Install with: pip install mobi"
            )
        
        import shutil

        tempdir, filepath = mobi.extract(str(file_path))
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content_str = f.read()
            
            parser = EPUBMOBIHTMLParser()
            parser.feed(content_str)
            cleaned_text = parser.get_text()
        finally:
            shutil.rmtree(tempdir, ignore_errors=True)

        if not cleaned_text.strip():
            raise ValueError("No text content could be extracted from the MOBI file.")

        return cleaned_text


class EPUBMOBIHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.ignore_tags = {"script", "style", "nav", "header", "footer", "form", "noscript", "head", "iframe", "button"}
        self.ignore_stack = []

    def handle_starttag(self, tag, attrs):
        if tag in self.ignore_tags:
            self.ignore_stack.append(tag)
        elif not self.ignore_stack:
            if tag in {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"}:
                self.text_parts.append("\n")
            if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                try:
                    level = int(tag[1])
                except ValueError:
                    level = 2
                self.text_parts.append("#" * level + " ")

    def handle_data(self, data):
        if not self.ignore_stack:
            self.text_parts.append(data)

    def handle_endtag(self, tag):
        if self.ignore_stack and tag == self.ignore_stack[-1]:
            self.ignore_stack.pop()
        elif not self.ignore_stack:
            if tag in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"}:
                self.text_parts.append("\n")

    def get_text(self) -> str:
        raw_text = "".join(self.text_parts)
        cleaned = re.sub(r'[ \t]+', ' ', raw_text)
        cleaned = re.sub(r'\n\s*\n+', '\n\n', cleaned)
        return cleaned.strip()


HEADING_RE = re.compile(r'^(#{1,6})\s+(.*)$')


class PDFHeadingExtractor:
    """Derive markdown ATX headings from PDF font geometry.

    PDFs carry no semantic heading markup — a heading is only visually
    distinct. We reconstruct it heuristically from per-character font size
    (via ``page.chars``) plus a dotted-number prefix fallback, emitting the
    same ``#``-dialect the HTML parsers produce. This is the *heuristic*
    confidence tier of ADR-062; misses degrade gracefully to body text.
    """

    NUMBERING_RE = re.compile(r'^(\d+(?:\.\d+)*)\s+\S')

    @classmethod
    def extract(cls, file_path: Path, pdfplumber) -> str:
        line_records: list[tuple[str, float]] = []
        with pdfplumber.open(str(file_path)) as pdf:
            for page in pdf.pages:
                line_records.extend(cls._page_lines(page))

        if not line_records:
            return ""

        sizes = [size for _, size in line_records if size > 0]
        body_size = cls._mode(sizes) if sizes else 0.0

        distinct_larger = sorted(
            {round(s, 1) for s in sizes if s > body_size * 1.15},
            reverse=True,
        )
        size_to_level = {sz: min(idx + 1, 6) for idx, sz in enumerate(distinct_larger)}

        out: list[str] = []
        for text, size in line_records:
            level = cls._heading_level(text, size, body_size, size_to_level)
            if level:
                out.append("#" * level + " " + text.strip())
            else:
                out.append(text)
        joined = "\n".join(out)
        return re.sub(r'\n\s*\n+', '\n\n', joined).strip()

    @staticmethod
    def _page_lines(page) -> list[tuple[str, float]]:
        chars = page.chars or []
        if not chars:
            txt = page.extract_text()
            return [(line, 0.0) for line in (txt.split("\n") if txt else [])]

        lines: dict[float, list[dict]] = {}
        for ch in chars:
            key = round(ch.get("top", 0.0), 0)
            lines.setdefault(key, []).append(ch)

        records: list[tuple[str, float]] = []
        for key in sorted(lines):
            row = sorted(lines[key], key=lambda c: c.get("x0", 0.0))
            text = "".join(c.get("text", "") for c in row).strip()
            if not text:
                continue
            char_sizes = [c.get("size", 0.0) for c in row if c.get("size")]
            median_size = sorted(char_sizes)[len(char_sizes) // 2] if char_sizes else 0.0
            records.append((text, median_size))
        return records

    @classmethod
    def _heading_level(cls, text: str, size: float, body_size: float,
                       size_to_level: dict[float, int]) -> int:
        stripped = text.strip()
        if not stripped or len(stripped.split()) > 25:
            return 0
        if body_size and size > body_size * 1.15:
            rounded = round(size, 1)
            if rounded in size_to_level:
                return size_to_level[rounded]
            return 1
        m = cls.NUMBERING_RE.match(stripped)
        if m and len(stripped.split()) <= 12:
            depth = m.group(1).count(".") + 1
            return min(depth, 6)
        return 0

    @staticmethod
    def _mode(values: list[float]) -> float:
        counts: dict[float, int] = {}
        for v in values:
            r = round(v, 1)
            counts[r] = counts.get(r, 0) + 1
        return max(counts, key=counts.get) if counts else 0.0


def _heading_path_for_paragraphs(paragraphs: list[str]) -> list[list[str]]:
    """Compute the running heading ancestry for each paragraph.

    Walks the paragraph sequence maintaining a level-indexed heading stack.
    A paragraph beginning with markdown ATX headings (``#``..``######``)
    updates the stack; every paragraph is tagged with the ancestry in force
    at its position. The heading-path is a contingent striation recorded as
    metadata, never a governing structure (see ADR-062).
    """
    stack: dict[int, str] = {}
    paths: list[list[str]] = []
    for para in paragraphs:
        first_line = para.split("\n", 1)[0].strip()
        m = HEADING_RE.match(first_line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            for deeper in [lvl for lvl in stack if lvl >= level]:
                del stack[deeper]
            if title:
                stack[level] = title
        paths.append([stack[lvl] for lvl in sorted(stack)])
    return paths


class RhizomaticDigester(SimpleChunkDigester):
    def chunk_with_metadata(self, text: str, chunk_size: int = 512, overlap: int = 64) -> list[dict]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return []

        para_paths = _heading_path_for_paragraphs(paragraphs)

        chunks = []
        i = 0
        while i < len(paragraphs):
            current_chunk_paragraphs = []
            current_words_count = 0
            j = i
            while j < len(paragraphs):
                p_words = len(paragraphs[j].split())
                if current_words_count + p_words > chunk_size and current_chunk_paragraphs:
                    break
                current_chunk_paragraphs.append(paragraphs[j])
                current_words_count += p_words
                j += 1
            
            chunk_text = "\n\n".join(current_chunk_paragraphs)
            chunks.append({
                "text": chunk_text,
                "paragraph_indices": list(range(i, j)),
                "heading_path": para_paths[i] if i < len(para_paths) else []
            })
            
            advance = j - i
            if advance <= 1:
                i += 1
            else:
                overlap_words = 0
                overlap_count = 0
                for k in range(j - 1, i, -1):
                    p_words = len(paragraphs[k].split())
                    if overlap_words + p_words > overlap:
                        break
                    overlap_words += p_words
                    overlap_count += 1
                step = max(1, advance - max(1, overlap_count))
                i += step
        return chunks

    def chunk(self, text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
        chunks_meta = self.chunk_with_metadata(text, chunk_size, overlap)
        return [c["text"] for c in chunks_meta]

    def get_super_chunks(self, text: str, super_chunk_size: int = 4000) -> list[dict]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return []

        super_chunks = []
        i = 0
        while i < len(paragraphs):
            current_paragraphs = []
            current_words = 0
            j = i
            while j < len(paragraphs):
                p_words = len(paragraphs[j].split())
                if current_words + p_words > super_chunk_size and current_paragraphs:
                    break
                current_paragraphs.append(paragraphs[j])
                current_words += p_words
                j += 1
            
            super_chunks.append({
                "text": "\n\n".join(current_paragraphs),
                "start_paragraph_idx": i,
                "end_paragraph_idx": j - 1,
            })
            i = j
        return super_chunks


def get_preview(text: str, max_chars: int = 200) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."

