"""Document text extraction and chunking for the knowledge base."""

import re
from io import BytesIO

SUPPORTED_SOURCE_TYPES = ("txt", "pdf")


class DocumentProcessingError(Exception):
    pass


class UnsupportedDocumentError(DocumentProcessingError):
    pass


def extract_text(content, filename):
    """Return ``(source_type, text)`` for supported document content."""
    source_type = _resolve_source_type(filename)

    if source_type == "txt":
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("utf-8", errors="replace")

    elif source_type == "pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise UnsupportedDocumentError(
                "PDF support requires the pypdf package"
            ) from exc
        try:
            reader = PdfReader(BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise DocumentProcessingError(f"Failed to read PDF: {exc}") from exc

    else:
        raise UnsupportedDocumentError(f"Unsupported source type: {source_type}")

    text = text.strip()
    if not text:
        raise DocumentProcessingError("No extractable text found in document")

    return source_type, text


def _resolve_source_type(filename):
    if "." not in filename:
        raise UnsupportedDocumentError("Filename must include an extension")
    extension = filename.rsplit(".", 1)[1].lower()
    if extension == "txt":
        return "txt"
    if extension == "pdf":
        return "pdf"
    raise UnsupportedDocumentError(
        f"Unsupported file type: .{extension}. Supported types: "
        + ", ".join(f".{item}" for item in SUPPORTED_SOURCE_TYPES)
    )


def split_text(text, max_chars=800, overlap=120):
    """Split text into overlapping chunks of roughly ``max_chars``."""
    if overlap >= max_chars:
        raise ValueError("overlap must be smaller than max_chars")

    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    chunks = []
    start = 0
    length = len(normalized)

    while start < length:
        end = min(start + max_chars, length)
        if end < length:
            window = normalized[start:end]
            boundary = max(
                window.rfind(" "),
                window.rfind(". "),
                window.rfind("? "),
                window.rfind("! "),
                window.rfind("; "),
            )
            if boundary > max_chars * 0.5:
                end = start + boundary + 1
        chunks.append(normalized[start:end].strip())
        if end >= length:
            break
        start = max(end - overlap, start + 1)

    return [chunk for chunk in chunks if chunk]