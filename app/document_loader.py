from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader


class UnsupportedFileTypeError(ValueError):
    """Raised when an uploaded file format is not supported."""


class EmptyDocumentError(ValueError):
    """Raised when no extractable text is found in a document."""


class CorruptedDocumentError(ValueError):
    """Raised when a document cannot be parsed."""


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def validate_supported_file(filename: str) -> str:
    """Validate the file extension and return it in lowercase."""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{suffix or 'unknown'}'. Supported types: {supported}."
        )
    return suffix


def extract_text_by_page(file_path: Path) -> list[dict[str, int | str | None]]:
    """Extract text from a supported document and preserve page metadata when available."""
    suffix = validate_supported_file(file_path.name)

    try:
        if suffix == ".pdf":
            pages = _extract_pdf(file_path)
        elif suffix == ".docx":
            pages = _extract_docx(file_path)
        else:
            pages = _extract_txt(file_path)
    except EmptyDocumentError:
        raise
    except Exception as exc:
        raise CorruptedDocumentError(f"Could not parse '{file_path.name}'.") from exc

    if not any(str(page["text"]).strip() for page in pages):
        raise EmptyDocumentError(f"Document '{file_path.name}' does not contain extractable text.")

    return pages


def _extract_pdf(file_path: Path) -> list[dict[str, int | str]]:
    """Extract text from each PDF page."""
    reader = PdfReader(str(file_path))
    pages: list[dict[str, int | str]] = []

    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append({"text": text, "page_number": index})

    return pages


def _extract_docx(file_path: Path) -> list[dict[str, str | None]]:
    """Extract text from DOCX paragraphs as a single logical document."""
    document = DocxDocument(str(file_path))
    paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    return [{"text": "\n".join(paragraphs), "page_number": None}]


def _extract_txt(file_path: Path) -> list[dict[str, str | None]]:
    """Extract text from a plain text file."""
    text = file_path.read_text(encoding="utf-8-sig")
    return [{"text": text, "page_number": None}]
