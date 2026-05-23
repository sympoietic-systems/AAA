import logging
from abc import ABC, abstractmethod
from pathlib import Path

from backend.utils.token_counter import estimate_tokens

logger = logging.getLogger(__name__)

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
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)


class RhizomaticDigester(SimpleChunkDigester):
    def chunk_with_metadata(self, text: str, chunk_size: int = 512, overlap: int = 64) -> list[dict]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return []

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
                "paragraph_indices": list(range(i, j))
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

